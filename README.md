# DuQuantum Pasqal: CVRP Quantum Pipeline

A reproducible **Track A + Track B** emulator submission: sequential quantum clustering, two TSP encodings, explicit global/DMM controls, exact evaluation, and honest failure/fallback accounting. All source and documents are in English. No hardware execution or quantum advantage is claimed.

## One-command reproduction

From the repository root with `uv` installed:

```bash
uv run --python 3.11 --with-requirements requirements.lock.txt python -m challenge.track_b
```

Using the existing project environment:

```bash
.venv/bin/python -m challenge.track_b
```

This generates 12 certified instances (S/M/L, seeds 11/29, uniform and heterogeneous demands), exact references, quantum and random baselines, 60 method rows, per-cluster evidence, plots, and the four-page report under `challenge/track_b_results/`. Quantum clustering uses at most 8 atoms per call; routing uses 10 edge or 16 position atoms for four-customer clusters. All computation is local. Full state-vector route simulation takes materially longer than the tutorials; runtime depends on hardware. No cloud credentials are needed.

For a small full-pipeline smoke run:

```bash
.venv/bin/python -m challenge.track_b --tiers M --seeds 11 --families uniform
```

A smoke run replaces the aggregate CSV/report with its selected subset. Run the default command again to restore the complete benchmark. Historical Track A outputs remain in `challenge/results/` and are never overwritten by Track B.

## What to read

- [Official requirements mapped to evidence](docs/challenge_contract.md)
- [Clustering model, formal CVRP, textbook slack, and atom accounting](challenge/MODEL.md)
- [Routing models, heterogeneous demands, DMM, evaluation, and limits](challenge/TRACK_B_MODEL.md)
- [Final four-page report](challenge/track_b_results/report.pdf)
- [End-to-end results](challenge/track_b_results/results.csv)
- [Per-cluster comparisons and fallback labels](challenge/track_b_results/clusters.csv)
- [Machine-readable result summary](challenge/track_b_results/summary.json)

## Follow the implementation

1. `challenge/core.py`: seeded generators, independently checked feasibility certificates, original-cost evaluation, exact references, and S-tier CPLEX cross-checks.
2. `challenge/quantum.py`: eight-customer quantum proposal window, constrained native embedding, legal global-detuning pulses, and saved conditional shot banks.
3. `challenge/run.py`: measured subset decoding, rejection without repair, and historical Track A benchmark.
4. `challenge/routing.py`: customer/position and undirected-edge TSP QUBOs, strict decoders, legal global or emulator-DMM pulses, and measured route selection.
5. `challenge/track_b.py`: merges quantum clustering and routing, keeps declared size fallbacks separate, and checks the absolute loss identity.
6. `challenge/summarize_b.py` and `challenge/report_b.py`: regenerate metrics, plots, and the report directly from saved evidence without changing quantum choices.

## Verify or rebuild the report

```bash
.venv/bin/python -m unittest challenge.test_challenge challenge.test_routing -v
.venv/bin/python -m challenge.summarize_b
.venv/bin/python -m challenge.report_b
```

Tests exhaustively inspect all 1024 edge and 65536 position bitstrings for a four-customer fixture. They also check certificates, exact references against independent solvers, route coverage/capacity, native geometry, raw shot counts, and loss decomposition. Full saved-evidence tests expect the complete default benchmark.

The original Track A benchmark remains reproducible with `python -m challenge.run`. Tutorial scripts remain in `examples/` with their English guides and outputs.

## Limits that matter

- Capacity is enforced by rejecting measured assignments, not by an exact analog capacity penalty. Heterogeneous remaining-load checks are necessary but not sufficient for completion.
- Sequential choices and the seeded eight-customer window restrict search. Certificates and exact references are never used to repair a quantum choice.
- Both TSP QUBOs are implemented and tested. Edge encoding uses fewer atoms; degree-only edge constraints are exact here only for at most four customers. Larger clusters use an explicitly declared classical size fallback.
- Clusters of at most three customers are trivial and excluded from quantum routing metrics. A failed four-customer quantum run stays failed; it is not classically repaired.
- DMM routing is emulator-only and reported separately from global-only control. Coupling and linear errors are saved; all physical long-range interactions remain.
- Finite conditional banks and best-of-shot selection are hybrid costs. Raw conditional hit rates are not unconditional CVRP success probabilities. Random valid-route sampling is a strong baseline on these small clusters.
- The report records failed embeddings/encodings, missing feasible trajectories, classical contributions, and AI use. A model-selected clustering can have a worse CVRP route than another clustering.
