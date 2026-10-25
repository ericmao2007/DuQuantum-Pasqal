"""Build an English tuning report from persisted experiment evidence."""
import csv
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).parent
OUT = ROOT/'tuning_results'


def build():
    summary = json.loads((OUT/'summary.json').read_text())
    selected = json.loads((OUT/'selected.json').read_text())
    protocol = json.loads((OUT/'protocol.json').read_text())
    with (OUT/'validation.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    by_case = {(r['instance'], r['candidate']): r for r in rows}
    text = '''# Sampler tuning experiment

This experiment tunes Track A clustering proposals. It does not change the clustering objective, capacity checks, exact reference solver, or Track B TSP algorithm. Quantum evolution is simulated classically using noiseless QutipBackendV2; these measurements do not demonstrate quantum speedup.

## Protocol

The protocol and complete candidate grid are in `tuning_results/protocol.json`. They were written before the first simulation. Four training cases use seed 11: M/L, uniform/heterogeneous demands. Six held-out cases use seed 101: S/M/L, both demand families. The held-out seed was excluded from parameter selection in this experiment; this is a newly run validation split, not a claim that seed 101 has never appeared anywhere else in the repository.

The search screens 16 configurations plus the original baseline. It varies peak Rabi frequency (4 or 8 rad/us), energy scale (2 or 4), subset reward multiplier (0.8 or 1.2), pulse duration (2000 or 5200 ns), and uses three geometric initializations per candidate. Baseline settings are omega=6, scale=4, reward=1, duration=5200 ns, one initialization. Geometry optimization tries a grid, a circle, and a permuted grid and retains the best legal coupling fit. This is a joint search, not an ablation establishing which individual parameter caused a change.

Screening measures only the first decision on each training case, using a 1000-shot bank. Its score is the observed probability of feasible subsets within the lowest 10% of that candidate's feasible stage-energy range. The stage reward changes across candidates, so this is only a screening proxy. Enumeration is used for evaluation, never to repair or select a solver output. The two highest screening candidates and baseline advance to full-pipeline training, with 32 trajectories each.

Full-pipeline selection first maximizes the number of training cases with at least one feasible solution. Ties maximize mean(feasibility rate - 0.25 * min(relative model gap, 2)); a failed case receives gap=2. The model objective always uses balance weight 0.15. The winning configuration is saved before evaluating held-out cases. No validation-based reselection is performed.

Each baseline/selected comparison uses the same instance, sampler seed, 32 trajectories, and 1000 shots per conditional bank. Conditional banks are reused, so trajectories share finite-bank estimation error. Different proposals visit different branches and therefore make different numbers of backend calls: this is not an equal-total-shot comparison. Exact routing evaluates the produced groups; it does not optimize the clustering proposals. No failed trajectory is repaired.

## Selected configuration

```json
'''
    text += json.dumps(selected, indent=2) + '\n```\n\n'
    text += '## Held-out results\n\n'
    text += '| Instance | Baseline feasible / 32 | Selected feasible / 32 | Baseline model gap | Selected model gap |\n|---|---:|---:|---:|---:|\n'
    for case in protocol['heldout']:
        a,b = [by_case[case,label] for label in ['baseline','selected']]
        fmt = lambda r: f"{float(r['model_gap_percent']):.2f}%" if r['model_gap_percent'] else 'No feasible solution'
        text += f"| {case} | {a['feasible_attempts']} | {b['feasible_attempts']} | {fmt(a)} | {fmt(b)} |\n"
    text += '\n| Metric | Baseline | Selected |\n|---|---:|---:|\n'
    for key,label in [('solved','Cases solved / 6'),('mean_feasibility','Mean feasible trajectory fraction'),('mean_model_gap_solved','Mean best model gap on solved cases (%)'),('mean_cvrp_gap_solved','Mean best observed route gap on solved cases (%)'),('total_seconds','Total held-out solver wall time (s)'),('backend_calls','Backend calls'),('backend_shots','Backend shots')]:
        a,b = [summary['validation'][k][key] for k in ['baseline','selected']]
        text += f'| {label} | {a:.4f} | {b:.4f} |\n'
    common = [case for case in protocol['heldout'] if all(by_case[case,k]['model_gap_percent'] for k in ['baseline','selected'])]
    gaps = {k: float(np.mean([float(by_case[case,k]['model_gap_percent']) for case in common])) for k in ['baseline','selected']}
    text += f"\nOn the {len(common)} cases solved by both methods, mean best model gap is {gaps['baseline']:.2f}% baseline versus {gaps['selected']:.2f}% selected. Compare this paired subset alongside failures; solved-only averages can hide failed cases. Route gaps above select the best route among feasible trajectories, which can differ from the best-model trajectory.\n"
    screen = list(csv.DictReader((OUT/'screening.csv').open()))
    training = list(csv.DictReader((OUT/'training.csv').open()))
    total_calls = len(screen) + sum(int(r['backend_calls']) for r in training+rows)
    total_shots = 1000*len(screen) + sum(int(r['backend_shots']) for r in training+rows)
    text += f"\nThe complete experiment took {summary['wall_seconds']:.1f} seconds ({summary['wall_seconds']/60:.2f} minutes), including exact evaluation references. It used {total_calls} backend calls and {total_shots:,} measured simulator shots. The search ran {len(screen)} screening jobs, {len(training)} full training jobs and {len(rows)} held-out jobs. Runtime depends on this machine and is not QPU runtime.\n"
    text += '''
## Interpretation and limits

Feasibility is the fraction of 32 full trajectories satisfying every capacity constraint. A model gap of 10% means the best observed F is 1.10 times the exact minimum F. A route gap compares an observed plan's exact within-group tours with the exact overall CVRP optimum. Improving F does not guarantee a shorter CVRP route.

This is a bounded pilot search with one instance seed per split and one sampling seed per case. Shared customer coordinates across demand families and shared finite banks reduce independence. There are no repeated-seed confidence intervals and no claim of universal improvement. The baseline remains available and default; the selected configuration is opt-in. Failure results and all screen candidates are retained. TSP pulse parameters were not tuned in this experiment.

## Reproduce and use

Run from the repository root:

```bash
.venv/bin/python -m challenge.tune
.venv/bin/python -m challenge.report_tuning
.venv/bin/python -m unittest challenge.test_challenge challenge.test_routing challenge.test_space challenge.test_tuning
```

Rerunning the experiment overwrites `challenge/tuning_results`. To use the frozen settings in an existing benchmark:

```bash
.venv/bin/python -m challenge.track_b --sampler-config challenge/tuning_results/selected.json
```

The custom benchmark writes separate `track_b_tuned_results` outputs and does not regenerate the baseline PDF template. Omitting the flag retains the historical baseline output path and behavior. Track A accepts the same flag and writes `tuned_results`. Raw shot counts, serialized pulse sequences, atom layouts, training metrics, references and validation outcomes are saved under `challenge/tuning_results`.
'''
    (ROOT/'TUNING.md').write_text(text)


if __name__ == '__main__':
    build()
