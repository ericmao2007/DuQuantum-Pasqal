"""Run the Track A benchmark: python -m challenge.run."""
import argparse
import csv
import json
import time
from pathlib import Path
import numpy as np
from .core import (TIERS, generate, validate, references, pair_costs, clustering_cost,
                   groups_to_assignment, canonical)
from .quantum import Sampler, WINDOW, PULSES, SCALE, BANK_SHOTS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'challenge' / 'results'


def evaluate(instance, reference, route_costs, route_orders, method, seed, attempts, record_trace=False):
    rng = np.random.default_rng(seed)
    pair = pair_costs(instance)
    sampler = Sampler(instance, pair, method, seed)
    feasible, plans = [], []
    stage_valid = stage_total = 0
    start = time.perf_counter()
    n, k = len(pair), instance['vehicles']
    demands = instance['demands']
    capacity = instance['capacity']
    # A necessary load bound only; heterogeneous packability is not solved classically.
    for attempt in range(attempts):
        remaining, groups = set(range(n)), []
        failed = False
        stages = []
        for left in range(k, 1, -1):
            if not remaining:
                break
            selected = sampler.draw(remaining, left, rng)
            stage_total += 1
            if record_trace:
                stages.append(dict(vehicle=k-left,remaining=sorted(remaining),pool=list(map(int,sampler.pool(remaining))),selected=selected,selected_load=sum(demands[i] for i in selected),remaining_load=sum(demands[i] for i in remaining.difference(selected)),vehicles_left=left))
            # Empty vehicles are valid. Reject, rather than repair, bad shots.
            if sum(demands[i] for i in selected) > capacity or sum(demands[i] for i in remaining.difference(selected)) > (left-1)*capacity:
                if record_trace:
                    stages[-1]['accepted']=False
                    stages[-1]['reason']='capacity exceeded' if stages[-1]['selected_load']>capacity else 'remaining fleet capacity insufficient'
                failed = True
                break
            if record_trace:
                stages[-1]['accepted']=True
                stages[-1]['reason']='capacity checks passed'
            stage_valid += 1
            groups.append(selected)
            remaining.difference_update(selected)
        if failed or sum(demands[i] for i in remaining) > capacity:
            failure={'attempt': attempt, 'feasible': False}
            if record_trace:
                failure['stages']=stages
            plans.append(failure)
            continue
        groups.append(sorted(remaining))
        assignment = groups_to_assignment(n, groups)
        loads = validate(instance, assignment)
        groups = canonical(groups)
        model = clustering_cost(groups, pair)
        masks = [sum(1 << i for i in g) for g in groups]
        route = sum(route_costs[m] for m in masks)
        plan = dict(attempt=attempt, feasible=True, groups=groups, loads=loads,
                    model_cost=model, routed_cost=route,
                    routes=[list(route_orders[m]) for m in masks])
        if record_trace:
            plan['stages']=stages
        plans.append(plan)
        feasible.append(plan)
    best = min(feasible, key=lambda p: (p['model_cost'], p['routed_cost'])) if feasible else None
    best_route = min(feasible, key=lambda p: p['routed_cost']) if feasible else None
    near = sum(p['model_cost'] <= reference['model_optimum'] * (1 + 1e-8) for p in feasible)
    errors = [b['relative_coupling_error'] for b in sampler.banks]
    atoms = max((len(b['pool']) for b in sampler.banks), default=min(WINDOW, n))
    row = dict(instance=instance['id'], method=method, seed=seed, track='A', attempts=attempts,
               feasible_attempts=len(feasible), feasibility_rate=len(feasible) / attempts,
               probability_model_reference=near / attempts, reference_epsilon_percent=1e-6,
               model_gap_percent=None if best is None else 100 * (best['model_cost'] / reference['model_optimum'] - 1),
               cvrp_gap_percent=None if best is None else 100 * (best_route['routed_cost'] / reference['cvrp_optimum'] - 1),
               best_model_cost=None if best is None else best['model_cost'],
               model_selected_cvrp_gap_percent=None if best is None else 100*(best['routed_cost']/reference['cvrp_optimum']-1),
               best_cvrp_routed_cost=None if best_route is None else best_route['routed_cost'],
               probability_cvrp_reference=sum(p['routed_cost'] <= reference['cvrp_optimum']*(1+1e-8) for p in feasible)/attempts,
               best_shot_exact_routed_cost=None if best is None else best['routed_cost'],
               peak_atoms=atoms, slack_atoms=0, sequential_calls_per_attempt_max=k-1,
               raw_stage_feasibility_rate=stage_valid / stage_total if stage_total else 0,
               embedding_error_mean=float(np.mean(errors)) if errors else None,
               embedding_error_max=max(errors) if errors else None,
               backend_calls=sampler.backend_calls, backend_shots=sampler.backend_shots,
               sample_bank_shots=BANK_SHOTS if method != 'random' else 0,
               sampling_protocol='independent trajectories resampled from finite cached conditional shot banks' if method != 'random' else 'independent fair bits; same window and rejection',
               backend='QutipBackendV2 exact state-vector' if method != 'random' else 'numpy random',
               bond_dimension='not applicable: no MPS truncation', global_detuning_only=True, noise=False,
               modulation=False, reference_status=reference['status'],
               elapsed_seconds=time.perf_counter()-start,
               backend_and_embedding_seconds=sampler.backend_seconds,
               total_demand=sum(instance['demands']), load_ratio=sum(instance['demands'])/(k*instance['capacity']),
               largest_demand_ratio=max(instance['demands'])/instance['capacity'])
    detail = dict(metrics=row, best_plan=best, best_cvrp_plan=best_route, attempts=plans, banks=sampler.banks)
    return row, detail


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tiers', nargs='+', choices=list(TIERS), default=list(TIERS))
    parser.add_argument('--seeds', nargs='+', type=int, default=[11, 29])
    parser.add_argument('--attempts', type=int, default=32)
    parser.add_argument('--methods', nargs='+', choices=['fast', 'slow', 'random'], default=['fast', 'slow', 'random'])
    args = parser.parse_args()
    if args.attempts < 1:
        parser.error('--attempts must be positive')
    OUT.mkdir(exist_ok=True)
    (ROOT/'challenge'/'instances').mkdir(exist_ok=True)
    rows = []
    for tier in args.tiers:
        for seed in args.seeds:
            instance = generate(tier, seed)
            name = instance['id']
            (ROOT/'challenge'/'instances'/f'{name}.json').write_text(json.dumps(instance, indent=2)+'\n')
            print(f'Computing exact references for {name}', flush=True)
            ref_start = time.perf_counter()
            reference, costs, orders = references(instance)
            reference['evaluation_seconds'] = time.perf_counter()-ref_start
            (OUT/f'{name}_reference.json').write_text(json.dumps(reference, indent=2)+'\n')
            print(f'  model={reference["model_optimum"]:.4f}, CVRP={reference["cvrp_optimum"]:.4f}', flush=True)
            for method in args.methods:
                row, detail = evaluate(instance, reference, costs, orders, method, seed+10000, args.attempts)
                rows.append(row)
                (OUT/f'{name}_{method}.json').write_text(json.dumps(detail, indent=2)+'\n')
                print(f'  {name} {method}: feasibility={row["feasibility_rate"]:.1%}, model gap={row["model_gap_percent"]}', flush=True)
                with (OUT/'results.csv').open('w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
    settings = dict(tiers=args.tiers, seeds=args.seeds, attempts=args.attempts, methods=args.methods,
                    max_atoms=WINDOW, pulse_durations_ns=PULSES, energy_scale=SCALE,
                    quantum_bank_shots=BANK_SHOTS, certificate_used_by_optimizer=False,
                    reference_used_by_optimizer=False, dmm=False)
    (OUT/'settings.json').write_text(json.dumps(settings, indent=2)+'\n')
    print(f'Wrote {OUT / "results.csv"}', flush=True)
    from .report import build
    build()


if __name__ == '__main__':
    main()
