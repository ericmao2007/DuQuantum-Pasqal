# DuQuantum Pasqal Challenge

A reproducible **Track A** baseline for the CVRP challenge: sequential, slack-free, global-detuning quantum clustering with at most eight atoms at once. Exact classical routing is used for evaluation, not presented as quantum routing. Code and documents are in English.

## Reproduce

From this directory, with `uv` installed:

```bash
uv run --python 3.11 --with-requirements requirements.lock.txt python -m challenge.run
```

For the existing project environment:

```bash
.venv/bin/python -m challenge.run
```

This regenerates six certified instances (S/M/L, seeds 11 and 29), exact references, two quantum pulse baselines and a random baseline, and `challenge/results/results.csv`. Each row has 32 full sequential attempts. Runtime depends on hardware; quantum banks and reference evaluation are classical simulations. The command needs no cloud credentials. Offline after dependency installation, use the `.venv` command.

Quick smoke run (overwrites the aggregate CSV with only the requested rows):

```bash
.venv/bin/python -m challenge.run --tiers S --seeds 11 --attempts 8
```

Full reruns replace matching result files. Run the default command again to restore the complete benchmark CSV.

## Read the work

- [Model, derivations, variable accounting, and limitations](challenge/MODEL.md)
- [Instance generator, validator, and exact references](challenge/core.py)
- [Embedding and legal Pulser pulses](challenge/quantum.py)
- [Benchmark runner and metric definitions](challenge/run.py)
- [Results CSV](challenge/results/results.csv)
- [Programming with Pulser tutorial](examples/README.md)
- [Register and blockade tutorial](examples/REGISTER_INTERACTIONS.md)

The current benchmark deliberately uses equal demands. Capacity is enforced by rejecting measured subsets, not by an exact capacity penalty in the Hamiltonian. A seeded eight-customer window and sequential decisions limit the search space. The final vehicle receives the remainder. Coupling error, failures, finite cached-bank sampling, and random-baseline comparisons are reported explicitly. This is not a heterogeneous-demand solver, Track B quantum-routing submission, or quantum-advantage claim.

## Follow the pipeline step by step

1. Read `challenge/MODEL.md`: distinguish the actual CVRP objective from the compact-clustering surrogate and from the approximate native energy.
2. `generate()` creates locations and demands from a seed. The certificate proves feasibility; `validate()` checks exact coverage and loads.
3. `Sampler.pool()` takes a seeded, geometry-independent window. Each atom represents whether its customer joins the current vehicle.
4. `embed()` fits the positive target couplings with physical distances. Saved errors show how much information this approximation loses.
5. `Sampler.draw()` builds a global-detuning Pulser sequence and obtains a 1000-shot conditional bank from QutipBackendV2.
6. `evaluate()` draws one subset per vehicle stage, rejects infeasible choices, and keeps every full trajectory in the feasibility denominator. It performs no repair or search.
7. `references()` runs expensive exact solvers strictly for scoring. Classical TSP turns each sampled clustering into a travel-distance score.
8. `report.build()` creates the comparison plots and four-page English report. Inspect both model and CVRP gaps, not just the best-looking metric.

## Verification

```bash
.venv/bin/python -m unittest challenge.test_challenge -v
.venv/bin/python -m challenge.report
```

The tests independently check certificates, invalid assignments, integer slack penalties, exact references against brute force and CPLEX, and saved physical layouts and feasible trajectories. The report source is `challenge/report.py`; its output is `challenge/results/report.pdf`.

The exploratory log-coupling-fit baseline is retained in `challenge/experiments/log_loss_baseline.csv` to document a failed embedding choice. Its errors should not be confused with the final squared-coupling-fit benchmark. The report records what did not work and the use of AI.
