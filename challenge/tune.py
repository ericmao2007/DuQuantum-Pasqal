"""Reproducible, split-before-search tuning of the Track A proposal sampler."""
import csv
import itertools
import json
import time
from pathlib import Path
import numpy as np
from .core import generate, generate_heterogeneous, pair_costs, references, BALANCE
from .quantum import Sampler
from .run import evaluate

OUT = Path(__file__).parent / 'tuning_results'


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def table(name, rows):
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def instances(seed, tiers):
    return [factory(tier, seed) for tier in tiers
            for factory in (generate, generate_heterogeneous)]


def selection_score(rows):
    """Prioritize solved cases, then feasibility with a model-quality penalty."""
    solved = sum(r['best_model_cost'] is not None for r in rows)
    utility = np.mean([r['feasibility_rate'] - .25 *
                       (min(r['model_gap_percent'] / 100, 2)
                        if r['model_gap_percent'] is not None else 2) for r in rows])
    return solved, float(utility)


def main():
    OUT.mkdir(exist_ok=True)
    started = time.perf_counter()
    train = instances(11, ['M', 'L'])
    heldout = instances(101, ['S', 'M', 'L'])
    candidates = {'baseline': {}}
    for omega, scale, reward, durations in itertools.product(
            [4., 8.], [2., 4.], [.8, 1.2], [[400, 1200, 400], [800, 3600, 800]]):
        name = f'candidate_{len(candidates):02d}'
        candidates[name] = dict(omega=omega, scale=scale, reward_factor=reward,
                                durations=durations, embedding_starts=3)
    # Protocol is persisted before any simulation or reference computation.
    save('protocol.json', dict(training=[x['id'] for x in train],
         heldout=[x['id'] for x in heldout], candidates=candidates,
         screening='First decision only: probability of feasible subsets in the lowest 10% of feasible stage-energy range.',
         advancement='Top two screen candidates plus baseline; full-pipeline training only selects the winner.',
         selection='Lexicographic: solved training cases, mean(feasibility - 0.25 * capped model relative gap). Missing gap=2; cap=2.',
         attempts=32, bank_shots=1000, sampler_seed_offset=10000,
         scope='Track A clustering proposals; routing algorithm and objective unchanged.',
         limitations='One instance seed per split; finite cached shot banks; noiseless classical quantum simulation.'))
    screen = []
    for name, options in candidates.items():
        for instance in train:
            pair = pair_costs(instance)
            sampler = Sampler(instance, pair, 'slow', 10011, options=options)
            remaining = set(range(len(pair)))
            sampler.draw(remaining, instance['vehicles'], np.random.default_rng(10011))
            bank = sampler.banks[0]
            pool = bank['pool']
            mu = options.get('reward_factor', 1.) * 2 * BALANCE * len(pair) / instance['vehicles']
            values = {}
            for bits in itertools.product('01', repeat=len(pool)):
                selected = [i for i, bit in zip(pool, bits) if bit == '1']
                load = sum(instance['demands'][i] for i in selected)
                feasible = (load <= instance['capacity'] and
                    sum(instance['demands']) - load <= (instance['vehicles']-1)*instance['capacity'])
                if feasible:
                    energy = BALANCE*len(selected)**2 - mu*len(selected)
                    energy += sum(pair[i, j] for i, j in itertools.combinations(selected, 2))
                    values[''.join(bits)] = energy
            threshold = min(values.values()) + .1*(max(values.values())-min(values.values()))
            counts = bank['counts']
            row = dict(candidate=name, instance=instance['id'],
                good_probability=sum(c for b,c in counts.items() if b in values and values[b] <= threshold)/1000,
                feasible_probability=sum(c for b,c in counts.items() if b in values)/1000,
                embedding_error=bank['relative_coupling_error'], seconds=sampler.backend_seconds)
            screen.append(row)
            save(f'screen_{name}_{instance["id"]}.json', bank)
            table('screening.csv', screen)
            print('SCREEN', row, flush=True)
    ranked = sorted((name for name in candidates if name != 'baseline'), reverse=True,
        key=lambda name: tuple(np.mean([r[key] for r in screen if r['candidate']==name])
                               for key in ['good_probability','feasible_probability']))
    finalists = ['baseline'] + ranked[:2]
    training = []
    for instance in train:
        ref, costs, orders = references(instance)
        save(f'{instance["id"]}_reference.json', ref)
        for name in finalists:
            row, detail = evaluate(instance, ref, costs, orders, 'slow', 10011, 32,
                                   sampler_options=candidates[name])
            row['candidate'] = name
            training.append(row)
            save(f'train_{name}_{instance["id"]}.json', detail)
            table('training.csv', training)
            print('TRAIN', name, instance['id'], selection_score([row]), flush=True)
    winner = max(finalists, key=lambda name: selection_score([r for r in training if r['candidate']==name]))
    # Freeze before touching held-out instances. Never reselect using validation.
    save('selected.json', dict(candidate=winner, sampler_options=candidates[winner],
        finalists=finalists, training_scores={name: selection_score([r for r in training if r['candidate']==name]) for name in finalists}))
    validation = []
    for instance in heldout:
        ref, costs, orders = references(instance)
        save(f'{instance["id"]}_reference.json', ref)
        for label, options in [('baseline', {}), ('selected', candidates[winner])]:
            row, detail = evaluate(instance, ref, costs, orders, 'slow', 10101, 32,
                                   sampler_options=options)
            row['candidate'] = label
            validation.append(row)
            save(f'validation_{label}_{instance["id"]}.json', detail)
            table('validation.csv', validation)
            print('VALIDATION', label, instance['id'], selection_score([row]), flush=True)
    summary = dict(winner=winner, sampler_options=candidates[winner],
                   wall_seconds=time.perf_counter()-started, validation={})
    for label in ['baseline', 'selected']:
        rows = [r for r in validation if r['candidate']==label]
        summary['validation'][label] = dict(instances=len(rows),
            solved=sum(r['best_model_cost'] is not None for r in rows),
            mean_feasibility=float(np.mean([r['feasibility_rate'] for r in rows])),
            mean_model_gap_solved=float(np.mean([r['model_gap_percent'] for r in rows if r['model_gap_percent'] is not None])),
            mean_cvrp_gap_solved=float(np.mean([r['cvrp_gap_percent'] for r in rows if r['cvrp_gap_percent'] is not None])),
            total_seconds=sum(r['elapsed_seconds'] for r in rows),
            backend_shots=sum(r['backend_shots'] for r in rows),
            backend_calls=sum(r['backend_calls'] for r in rows))
    save('summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
