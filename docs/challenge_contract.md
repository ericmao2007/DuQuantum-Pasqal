# Challenge contract

Source: user-supplied `Pasqal-challenge-final.pdf`, Quantum Hackathon Pasqal version 3.0, updated 24 October 2026. This supersedes the preparation-only uncertainty in the earlier team roadmap.

## Official task

CVRP with fixed depot, symmetric metric distances, indivisible customer deliveries, identical fixed fleet, no reloading, and optional unused vehicles. Use cluster-first / route-second. Track A requires capacity-feasible clustering; Track B additionally requires two routing encodings and quantum routing evidence, with honest fallback labeling.

Prescribed tiers: S=(4 customers,2 vehicles,capacity7,demands1..4); M=(10,3,20,1..8); L=(15,4,30,1..10). Depot and customers lie in a square of side100. Generate reproducible certified-feasible instances and report load and largest-demand ratios.

Use emulators during the hackathon; hardware is explicitly not required. AnalogDevice envelope: 80 atoms, 5 um minimum separation, 38 um radius, Omega<=12.57 rad/us, global detuning in +/-125.66 rad/us, duration<=6000 ns. DMM is allowed only as a separately labeled emulation variant, with nonpositive extra detuning and weights in [0,1]. No mandatory cloud access or credentials.

## Required evidence and submitted locations

| Requirement | Evidence |
|---|---|
| One-command reproduction and pins | README.md, requirements.lock.txt |
| Formal CVRP, textbook slack, variable counts | challenge/MODEL.md |
| TSP models, two encodings, controls, limitations | challenge/TRACK_B_MODEL.md |
| Generators, feasibility certificates and validator | challenge/core.py, challenge/track_b_results/instances/ |
| Native geometry, pulses, raw bitstrings | challenge/quantum.py, challenge/routing.py, saved banks |
| Classical references and S CPLEX/brute-force agreement | saved reference JSON, automated tests |
| Original Track A pulse/random comparisons | challenge/results/results.csv |
| Complete pipeline metrics | challenge/track_b_results/results.csv |
| Per-cluster routing and fallback accounting | challenge/track_b_results/clusters.csv |
| Four-page final report and AI disclosure | challenge/track_b_results/report.pdf |

All gaps use feasible decoded solutions and original relevant costs. Missing feasible outcomes have undefined gaps. Canonicalized customer groups remove identical-vehicle relabelings. Trivial clusters n<=3 are excluded from quantum routing metrics; clusters above the declared four-customer execution limit use exact classical fallback and remain visible in coverage metrics.

## Remaining external details

The supplied brief does not give a concrete submission timestamp, presentation length, or upload portal. This repository implements and packages the technical deliverables; it does not invent those logistics or claim external competition submission. GitHub push is authorized by the user.
