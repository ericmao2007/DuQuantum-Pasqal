# Complete pipeline: Track B models and accounting

This extends the original Track A baseline. Historical Track A results remain in `challenge/results/`. New evidence, including heterogeneous-demand instances, is in `challenge/track_b_results/`. All quantum computations are emulator runs; no hardware submission or quantum advantage is claimed.

## 1. Heterogeneous demand extension

`generate_heterogeneous(tier, seed)` first creates seeded coordinates and integer demands near the tier's baseline demand, within the prescribed range. It then reduces the largest demands in each cyclic certificate group until that group's load fits capacity. This construction guarantees a feasible assignment without using an optimization solver. The certificate is checked and never passed to the sampler.

The quantum clustering objective and eight-customer window are unchanged. Measured subsets are checked by actual demand sum, not customer count. The remaining total demand bound is necessary, but generally not sufficient for bin-packing feasibility. No exact packability solver is called online; the final vehicle is validated, and a failed trajectory remains a failure. This extends input support without falsely asserting an exact capacity Hamiltonian or guaranteed completion.

## 2. TSP for one cluster

For a fixed cluster C of n customers, include the fixed depot 0. Minimize the length of a Hamiltonian cycle on these n+1 locations, measured with the original Euclidean distances. All customers appear exactly once; the route starts and ends at the depot. Reversed cycles are equivalent for symmetric costs.

Routing cost coefficients use distances divided by 100 sqrt(2), putting every edge in [0,1]. Reported tour lengths and gaps always use original distance units. The penalty A=10 is chosen before seeing solutions. For the implemented n=4 limit, any valid tour costs at most five normalized units, whereas any nonzero squared integer constraint violation costs at least ten. Thus the target QUBO's exact ground state is feasible. Physical embedding error can still change its ground state.

### Position encoding

Use n^2 binary variables x_it: customer i occupies position t, with t=0,...,n-1 and the depot fixed outside those positions. Minimize

sum_i c_0i x_i0 + sum_i c_i0 x_i,n-1
+ sum_t=0..n-2 sum_i!=j c_ij x_it x_j,t+1
+ A sum_i(sum_t x_it-1)^2
+ A sum_t(sum_i x_it-1)^2.

Each variable has a -2A penalty linear term, plus any first/last-position depot cost. Constraint pair coefficients are positive 2A; travel pair coefficients are positive. The constant is 2nA. Strict decoding accepts only a permutation matrix. The target formulation is valid for any n, but the execution threshold is n<=4 because this implementation uses exact local state-vector simulation.

### Undirected edge encoding

Use one variable e_ij per unordered pair among depot and customers, for n(n+1)/2 variables. Minimize

sum_i<j c_ij e_ij + A sum_v(sum_edges_incident_to_v e_ij-2)^2.

Each edge has linear coefficient c_ij-6A; pairs of edges sharing a vertex have coefficient 2A; the constant is 4(n+1)A. Degree-two constraints alone permit disjoint subtours in general. For nontrivial execution the encoding is restricted to n=4; the degree argument applies for 2<=n<=4: there are at most five vertices, and a simple undirected cycle uses at least three vertices, so two disjoint cycles cannot fit. Consequently every degree-two solution is one Hamiltonian cycle. The decoder also checks connectivity. The code rejects larger edge encodings rather than silently treating a cycle cover as a TSP tour.

| Customers n | Position variables | Edge variables | Executed? |
|---|---:|---:|---|
| 1-3 | n^2 | n(n+1)/2 | Classical trivial clusters, as allowed |
| 4 | 16 | 10 | Both encoded and quantum simulated |
| 5 | 25 | 15 | Classical size fallback; degree-only edge model no longer exact |
| 10 | 100 | 55 | Classical size fallback; position also exceeds atom cap |
| 15 | 225 | 120 | Classical size fallback; both exceed atom cap |

This is a real encoding comparison, including execution failures. A zero valid-shot count is not replaced with an exact route. Only clusters larger than four receive the declared classical fallback. No threshold is chosen after seeing a failed run.

## 3. Native embedding and DMM controls

Both QUBOs have positive pair coefficients but many desired zeros. No pair of physical atoms is exactly uncoupled; all unwanted interactions remain in the simulator. Fit the full target J matrix with the original constrained SLSQP embedder. Report relative pair error including the zero target entries in the numerator. Use scale 0.1 rad/us per normalized energy unit. Coordinates satisfy AnalogDevice separation >=5 um and radius <=38 um, with at most 16 atoms.

Linear coefficients vary by edge or endpoint cost, so global detuning cannot reproduce them exactly. The global-only edge baseline projects h to its mean and reports the resulting linear residual. In particular, much of an edge tour's travel objective lives in h: global projection can erase that information. This baseline must not be described as an exact TSP Hamiltonian.

DMM experiments are emulator-only and labeled separately. Keep AnalogDevice's geometry, 80-atom limit, timing, amplitude, and global-detuning bounds; add a DMM with 4 ns clock, 6000 ns maximum pulse, bottom detuning -125.663706 rad/us, and total bottom detuning -10000 rad/us. These are declared emulation controls, not a hardware calibration.

For desired scaled h_i, let h_min=min_i h_i and D=max_i h_i-h_min. Set delta_global=-h_min, DMM detuning=-D, and epsilon_i=(h_i-h_min)/D (zero weights if D=0). Then -delta_global-epsilon_i delta_DMM=h_i, with weights in [0,1] and nonpositive DMM detuning. This raises selected atoms' excitation cost relative to the shared minimum and never requires the prohibited opposite-sign DMM action. Ramp the map from zero during the global detuning sweep.

Every route sequence uses a 800/3600/800 ns rise/sweep/fall schedule, Omega_max=6 rad/us, initial global detuning -12 rad/us, and zero final Omega. DMM and global controls run concurrently; Pulser validates the actual 5200 ns schedule. Store the serialized sequence, coordinates, all h/J coefficients, counts, and decoded valid routes. QutipBackendV2 uses a full state vector, without MPS bond truncation; library numerical solver defaults apply. Noise, modulation response, trap-layout calibration, and mimic_qpu are disabled.

## 4. End-to-end protocol

For each S/M/L tier, seeds 11 and 29, and uniform/heterogeneous family:

1. Generate and validate the feasibility certificate.
2. Run 32 sequential clustering trajectories with the slow quantum pulse and with uniform random bits. The finite-bank protocol is inherited from Track A.
3. Select the best feasible quantum clustering by model cost, without using exact references to change a measured assignment.
4. Route the same selected clusters with edge/global, edge/DMM, position/DMM, and random valid permutations. Run 2000 measured routing shots per nontrivial cluster for each quantum encoding. Random routing gets 2000 valid permutation samples and the best sampled tour; this is a strong baseline on four-customer clusters, where only 12 distinct undirected tours exist.
5. Route n<=3 clusters exactly and mark them trivial. Route n>4 exactly and mark them as classical size fallbacks. Neither category contributes to the quantum routing gap or quantum reference-hit probability, but both contribute to end-to-end length.
6. A failed nontrivial quantum-routed cluster makes that method's end-to-end solution unavailable. Do not fall back after a quantum failure. Save all failures and their raw feasibility rates.
7. Also evaluate the full random-clustering/random-routing pipeline. The exact reference algorithms do not enter either online optimizer.

The default experiment has 12 instances and five end-to-end methods per instance (60 rows). Three routing variants share each quantum clustering; their shared clustering cost must not be summed as independent work. Per-cluster records are in `clusters.csv`. Group sizes, methods, atom counts, raw feasibility/hit rates, embedding/linear errors, and fallback flags are explicit.

## 5. Gaps and absolute loss identity

Let C_ref be the exact full CVRP optimum, C_model the exact-routed optimum of the constrained clustering model, C_shot the exact-routed selected quantum clustering, and C_end the actual merged quantum/classical routes.

- Model gap compares selected clustering F with the exact constrained F optimum.
- CVRP gap compares C_shot with C_ref.
- Decomposition gap compares C_model with C_ref.
- Routing gap compares total quantum tour length with exact TSP on those same nontrivial, successfully quantum-routed clusters only. If any eligible quantum route fails, aggregate routing gap is undefined, not a success-only average.
- End-to-end gap compares C_end with C_ref, and is undefined after any unrecovered quantum route failure.

Absolute losses are decomposition=C_model-C_ref, clustering=C_shot-C_model, and routing=C_end-C_shot. The code asserts their sum equals C_end-C_ref. Clustering loss may be negative; it is not clipped. Quantum coverage counts successful nontrivial quantum-routed clusters divided by all nontrivial clusters, including declared classical fallbacks in the denominator. Trivial-only pipelines have undefined coverage and say nothing about quantum routing.

Reference-hit rates count all raw shots, including invalid shots. The product of per-cluster raw hit rates is conditional on the fixed selected clustering and independent conditional routing draws. It is not an unconditional full-CVRP success probability or the success probability of best-of-2000 selection. Shared clustering banks and model-based best-plan selection must be accounted for before making such a claim. End-to-end feasibility of the returned batch result is distinct from raw routing shot feasibility.

## 6. References, verification, and limits

The classical CVRP and clustering references enumerate all feasible subsets and solve exact set partitioning by an anchored dynamic program, counting unlabeled optimal partitions. Subset TSP is now evaluated with Held-Karp dynamic programming, avoiding factorial construction on heterogeneous instances. S references are independently checked with full assignment enumeration and CPLEX. A separate test compares Held-Karp tour costs with exhaustive permutation tours for every subset of a four-customer fixture.

Tests exhaustively inspect all 1024 edge bitstrings and 65536 position bitstrings for a four-customer fixture: the accepted counts are 12 and 24, respectively; every accepted energy equals normalized physical tour length; every invalid target energy lies above the optimum. This isolates target-encoding correctness from physical embedding failures. Further tests validate capacities, route coverage, native geometry, shot budgets, and the loss identity on saved results.

Classical fallback, reference evaluation, embedding, and measurement selection are substantial hybrid costs; no advantage claim is made. A valid target encoding is not sufficient evidence of a faithful physical embedding. In particular, position decoding may return no valid routes despite a correct target QUBO. All such cases remain in the result table.

AI assisted model derivation, implementation, experiments, tests, and reporting. The team owns the final model and should review the source and saved evidence before submission. The challenge brief and Lucas (2014), DOI https://doi.org/10.3389/fphy.2014.00005 , motivate standard squared-constraint constructions; this submission does not claim a novel exact encoding.
