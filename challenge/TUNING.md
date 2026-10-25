# Sampler tuning experiment

This experiment tunes Track A clustering proposals. It does not change the clustering objective, capacity checks, exact reference solver, or Track B TSP algorithm. Quantum evolution is simulated classically using noiseless QutipBackendV2; these measurements do not demonstrate quantum speedup.

## Protocol

The protocol and complete candidate grid are in `tuning_results/protocol.json`. They were written before the first simulation. Four training cases use seed 11: M/L, uniform/heterogeneous demands. Six held-out cases use seed 101: S/M/L, both demand families. The held-out seed was excluded from parameter selection in this experiment; this is a newly run validation split, not a claim that seed 101 has never appeared anywhere else in the repository.

The search screens 16 configurations plus the original baseline. It varies peak Rabi frequency (4 or 8 rad/us), energy scale (2 or 4), subset reward multiplier (0.8 or 1.2), pulse duration (2000 or 5200 ns), and uses three geometric initializations per candidate. Baseline settings are omega=6, scale=4, reward=1, duration=5200 ns, one initialization. Geometry optimization tries a grid, a circle, and a permuted grid and retains the best legal coupling fit. This is a joint search, not an ablation establishing which individual parameter caused a change.

Screening measures only the first decision on each training case, using a 1000-shot bank. Its score is the observed probability of feasible subsets within the lowest 10% of that candidate's feasible stage-energy range. The stage reward changes across candidates, so this is only a screening proxy. Enumeration is used for evaluation, never to repair or select a solver output. The two highest screening candidates and baseline advance to full-pipeline training, with 32 trajectories each.

Full-pipeline selection first maximizes the number of training cases with at least one feasible solution. Ties maximize mean(feasibility rate - 0.25 * min(relative model gap, 2)); a failed case receives gap=2. The model objective always uses balance weight 0.15. The winning configuration is saved before evaluating held-out cases. No validation-based reselection is performed.

Each baseline/selected comparison uses the same instance, sampler seed, 32 trajectories, and 1000 shots per conditional bank. Conditional banks are reused, so trajectories share finite-bank estimation error. Different proposals visit different branches and therefore make different numbers of backend calls: this is not an equal-total-shot comparison. Exact routing evaluates the produced groups; it does not optimize the clustering proposals. No failed trajectory is repaired.

## Selected configuration

```json
{
  "candidate": "candidate_10",
  "sampler_options": {
    "omega": 8.0,
    "scale": 2.0,
    "reward_factor": 0.8,
    "durations": [
      800,
      3600,
      800
    ],
    "embedding_starts": 3
  },
  "finalists": [
    "baseline",
    "candidate_14",
    "candidate_10"
  ],
  "training_scores": {
    "baseline": [
      3,
      0.27513271151087304
    ],
    "candidate_14": [
      3,
      0.21204519036080777
    ],
    "candidate_10": [
      4,
      0.28277756688639333
    ]
  }
}
```

## Held-out results

| Instance | Baseline feasible / 32 | Selected feasible / 32 | Baseline model gap | Selected model gap |
|---|---:|---:|---:|---:|
| S_101 | 13 | 16 | 0.00% | 0.00% |
| S_heterogeneous_101 | 31 | 31 | 0.00% | 0.00% |
| M_101 | 17 | 19 | 8.22% | 6.39% |
| M_heterogeneous_101 | 17 | 19 | 8.22% | 6.39% |
| L_101 | 22 | 19 | 15.76% | 17.67% |
| L_heterogeneous_101 | 13 | 12 | 18.28% | 14.94% |

| Metric | Baseline | Selected |
|---|---:|---:|
| Cases solved / 6 | 6.0000 | 6.0000 |
| Mean feasible trajectory fraction | 0.5885 | 0.6042 |
| Mean best model gap on solved cases (%) | 8.4140 | 7.5658 |
| Mean best observed route gap on solved cases (%) | 11.7407 | 11.1440 |
| Total held-out solver wall time (s) | 18.5866 | 43.4233 |
| Backend calls | 126.0000 | 153.0000 |
| Backend shots | 126000.0000 | 153000.0000 |

On the 6 cases solved by both methods, mean best model gap is 8.41% baseline versus 7.57% selected. Compare this paired subset alongside failures; solved-only averages can hide failed cases. Route gaps above select the best route among feasible trajectories, which can differ from the best-model trajectory.

The complete experiment took 170.2 seconds (2.84 minutes), including exact evaluation references. It used 713 backend calls and 713,000 measured simulator shots. The search ran 68 screening jobs, 12 full training jobs and 12 held-out jobs. Runtime depends on this machine and is not QPU runtime.

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
