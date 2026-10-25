# Planetary demo optimization

This update optimizes the fixed ten-planet 3D demo, not the official benchmark suite. All three ship tours still come from quantum edge/DMM measurements on a CPU simulator. No classical route fallback or reference plan is inserted.

| Metric | Previous demo | Updated demo |
|---|---:|---:|
| Total travel distance (su) | 517.932168 | 428.127519 |
| Exact CVRP reference (su) | 428.127519 | 428.127519 |
| Final optimality gap | 20.9761% | 0% within numerical precision |
| Clustering model gap | 12.0495% | 0% |
| Clustering attempts | 64 | 512 |
| Window orders | 1 | 4 |
| Routing shots per ship | 2000 | 16000 |

Travel distance falls by 17.34%. This is a higher-budget, instance-specific improvement, not evidence of better speed or generalization.

## What changed

The previous subset sampler always took the first eight remaining customers from one fixed permutation. The search now uses four seeded permutations (order seeds 2926 through 2929), with 128 trajectories per permutation. All rounds run; the reference optimum does not decide when to stop. Pulse settings, physical embedding objective, clustering weight 0.15, coordinates, demands and vehicle capacities remain unchanged.

The selected grouping minimizes the original clustering objective F across the actual capacity-feasible sampled trajectories. Exact route costs and optimal reference groups do not select it. Of 512 full trajectories, 334 are feasible. In this instance, the selected F-optimal grouping also matches the exact CVRP-optimal grouping. This coincidence is not a general equivalence between F and route distance.

Each selected group then receives its own edge/DMM simulation and 16000 measured bitstrings. The decoder rejects invalid patterns and selects the shortest measured legal cycle. Larger shot banks reduce the chance of missing a good route; they do not guarantee success on arbitrary instances.

## Result and evidence

| Ship | Planet IDs | Atoms | Valid shots / total | Selected length (su) |
|---|---|---:|---:|---:|
| 1 | 0, 1, 2, 3 | 10 | 51 / 16000 | 147.437171 |
| 2 | 4, 5, 6 | 6 | 1279 / 16000 | 141.412000 |
| 3 | 7, 8, 9 | 6 | 1178 / 16000 | 139.278347 |

Their sum equals the independently computed global optimum to floating-point precision. Every selected tour is present in its raw measurement bank, visits its assigned planets once, returns to the depot, and is a connected degree-two cycle. Classical code still fits geometry, checks capacity, decodes measurements and compares measured lengths. Quantum evolution is simulated, not executed on a QPU.

The reproducible final run took approximately 23.57 seconds on this machine, including reference evaluation and file output up to the recorded timer. It made 201 clustering backend calls (201000 shots) plus three routing calls (48000 shots). Conditional clustering banks are cached and reused, so trajectories share finite-bank estimation error. Preliminary diagnostic runs are additional work and are not included in this final-run timer. No speed comparison is claimed.

Evidence is under `space_demo_results/`: `optimization_baseline.json` preserves the prior headline metrics, `search_round_*.json` contain all four individual runs, `clustering.json` combines their full traces and banks, and `route_*.json` contain every routing count and serialized pulse. The exported webpage evidence contains the same raw banks. The webpage reads actual attempt and shot budgets from the data and displays the previous distance next to the new result.

```bash
.venv/bin/python -m challenge.space_demo --search-rounds 4 --attempts-per-round 128 --routing-shots 16000
.venv/bin/python -m unittest challenge.test_challenge challenge.test_routing challenge.test_space challenge.test_tuning
```

The historical baseline is not overwritten when the optimized run is regenerated. The earlier version remains in Git history. The original Track A and Track B reports and their benchmark outputs are unchanged.
