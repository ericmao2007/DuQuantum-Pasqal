# Team handoff and defense guide

## The claim we can defend

We implemented a reproducible neutral-atom optimization experiment for capacitated vehicle routing. We reduce the simultaneous atom count using sequential subset proposals, compare two TSP encodings, quantify physical approximation and decoding failures, and evaluate all outputs against exact classical references. The computation runs in a noiseless CPU quantum emulator. It does not establish quantum advantage, universal optimality, or an exact native encoding of every constraint.

The formal benchmark has 12 certified two-dimensional instances and 60 method rows. The optimized planetary demo is separate. It reaches the proven optimum on its fixed ten-point instance after increasing the compute budget. State both the success and the scope limitation.

## 1. Original optimization problem

A depot is fixed. N customers have positions and integer demands. K identical vehicles each have capacity Q. Serve every customer exactly once; a vehicle may be unused. Every used vehicle leaves the depot, visits its assigned customers once, and returns without reloading. Minimize the sum of all tour distances. Customers cannot split deliveries between vehicles.

For each customer i and vehicle k, y_ik is 1 when that vehicle serves that customer. Coverage is sum_k y_ik = 1. Capacity is sum_i d_i y_ik <= Q. The first is an equality; the second allows unused capacity. A full routing formulation additionally needs directed edge variables, visit/flow constraints, depot-trip bounds and subtour elimination. MATH_WRITEUP.md gives the full statement.

Having total demand <= total fleet capacity is necessary but insufficient: demands (2,2,2) cannot fit two capacity-3 vehicles. The supplied feasibility certificate proves that every generated instance admits at least one legal assignment. It is not handed to the optimizer as a solution.

## 2. Why split clustering and routing?

Deciding vehicle and visit position simultaneously costs approximately N^2 K binary variables before slack. The tiers give 32, 300 and 900 variables. Hardware allows at most 80 atoms, and exact emulation often becomes difficult at much smaller sizes.

We first choose groups, then order each group's visits. This saves simultaneous variables but sacrifices global exactness. A compact grouping is not necessarily a grouping with short depot tours. Finding the optimum of our clustering objective does not generally solve CVRP.

## 3. Clustering objective

For customer group S, its contribution is 0.15 |S|^2 plus normalized pair distances inside S. Sum over vehicles to get F. Normalization is distance/(100 sqrt(2)) for the official square and distance/(100 sqrt(3)) for the fictional cube. F is dimensionless, not a travel distance.

The squared-size term discourages imbalanced group sizes. The pair-distance term favors geographically close customers. Demand affects capacity validation, not the squared-size term; counting customers and counting cargo are different.

## 4. Textbook constraint penalties and slack

A coverage penalty A(sum_k x_ik - 1)^2 vanishes only when one vehicle is selected. A capacity equality of the form sum_i d_i x_ik = Q would incorrectly force full loads. Instead introduce nonnegative unused capacity s_k and write sum_i d_i x_ik + s_k = Q. Encode s_k with binary bits, then square the equality residual.

A binary slack register needs ceil(log2(Q+1)) bits per vehicle. Assignment plus slack costs 14, 45 and 80 variables on S/M/L, versus assignment-only counts 8, 30 and 60. Squaring produces dense assignment/slack interactions. Fewer variables and easier embedding are different goals.

For binary x, x^2=x. Expanding (sum_i d_i x_i - Q)^2 produces linear coefficients d_i^2-2Qd_i, pair coefficients 2d_i d_j, and a constant Q^2. Include slack bits as additional weighted variables. Constants shift energies but do not change the minimizer.

If the feasible certificate has objective U, F is nonnegative and a violated integer equality has residual squared at least 1, choosing each penalty weight greater than U makes an infeasible global minimum impossible in the exact target model. Physical embedding approximation can destroy that guarantee. This exact penalty derivation is not the algorithm we actually execute for capacity.

## 5. Actual sequential sampler

Take up to eight remaining customers from a seeded permutation. One atom represents one customer's inclusion in the next vehicle. A measured 1 selects that customer; 0 leaves it unassigned for later vehicles.

The target subset energy is s[0.15 m^2 + sum_(i<j) w_ij b_i b_j - mu m], with m=sum_i b_i and mu=2*0.15*|R|/L. Here R is the remaining customer set and L the number of vehicles left. The negative reward discourages empty selections. Ignoring pair costs and integer restrictions, the size-only expression is minimized at m=|R|/L. This is motivation, not a capacity guarantee.

After measurement, classical code checks selected load <= Q and remaining total load <= (L-1)Q. Failed choices are rejected. The remaining-load test is necessary but not sufficient under heterogeneous demands. The last vehicle takes the remainder and the complete assignment is validated. No certificate repair is used.

We traded exact analog capacity enforcement for fewer simultaneous atoms, repeated quantum preparations and classical rejection. The proposal window and sequential choices can exclude useful choices at individual steps. This limitation must be disclosed, not described as an equivalent compression of the original CVRP.

A conditional bank contains 1000 simulated measurements for a pool/detuning. Many trajectories resample the same empirical bank. Therefore 32 trajectories are not 32 independent state evolutions, and their success estimates share bank-estimation uncertainty. Backend calls and shots are reported separately.

## 6. What the atoms and lasers mean

An atom is a binary variable, not necessarily a customer. Ground state represents 0; Rydberg excitation represents 1. The atom's 2D physical position controls interactions. It is different from the customer's map/space position.

At the end of the pulse with zero drive, the native diagonal energy is -delta sum_i b_i + sum_(i<j) V_ij b_i b_j. V_ij=C6/r_ij^6 is positive. Closer atoms mean stronger positive pair penalties; arbitrary independent coupling matrices are unavailable. Pairs cannot be exactly uncoupled at finite distance. Global detuning supplies a shared linear coefficient, not arbitrary h_i.

Omega controls coherent transitions between the binary states. Delta controls their relative energy: positive global delta lowers the energy of excitation in the -delta n convention. Neither parameter is a classical bit-flip probability.

The baseline pulse ramps amplitude up, scans detuning and ramps amplitude down. Its three segments are 800/3600/800 ns (5.2 us total); a faster clustering option uses 400/1200/400 ns. Peak drive is 6 rad/us and initial detuning is -12 rad/us. These are finite-time heuristic schedules, not a guarantee of adiabatic ground-state preparation.

Physical checks enforce at least 5 um separation, at most 38 um register radius and at most 6000 ns duration, using Pulser AnalogDevice validation. Constrained SLSQP fits target couplings. A low-dimensional planar geometry usually cannot reproduce all desired pair coefficients. Report the relative L2 error over unordered pairs; mathematical correctness of the target QUBO is not correctness of the realized Hamiltonian.

DMM adds a nonpositive local detuning waveform with fixed weights in [0,1]. To implement target h_a, use global delta=-min(h), a DMM amplitude -range(h), and weights (h_a-min(h))/range(h). This recovers the linear coefficients in the emulator; it does not fix pair coupling errors. DMM results are separate from global-only results and are not a claim of available QPU controls in this challenge.

## 7. Two routing encodings

Position encoding uses x_it=1 when customer i occupies visit slot t. Row constraints require each customer once; column constraints require one customer per slot. Cost includes depot-to-first, adjacent-customer distances and last-to-depot. Squared one-hot penalties implement the constraints. It needs n^2 atoms: 16 for four customers. Both directions of a tour appear separately, so there are 24 valid assignments for the 12 undirected four-customer tours.

Edge encoding uses one variable for each unordered pair among the depot and customers. A selected edge is included in the tour. Cost is edge length plus A sum_v(degree_v-2)^2, with A=10 in normalized units. It needs n(n+1)/2 atoms: 10 for four customers, 6 for three customers. A valid four-customer register has 12 bitstrings representing the undirected tours.

Degree two is not generally enough to enforce one tour. A disconnected union of cycles also has degree two. With at most five vertices (four customers plus depot), two disjoint simple cycles cannot fit because each requires at least three vertices. From five customers onward, two triangles are a counterexample. The current edge model therefore supports 2 through 4 customers only. One-customer travel also needs a special treatment because one undirected edge must be traversed twice.

The formal benchmark uses exact classical trivial tours at n<=3, quantum routing at n=4, and an explicit exact classical size fallback above four. Failed n=4 measurement batches stay failed. The separate planetary demo uses quantum edge/DMM sampling even for its three-customer groups. This illustrates the full measurement pipeline but does not make trivial groups informative routing benchmarks.

The decoder checks a connected cycle visiting every required node. A drawn line crossing is not an extra node. During clustering, the webpage shows color/halos without route edges; only visit-order stages show routes.

## 8. Exact references and why they are separate

Held-Karp computes exact tours for each capacity-feasible subset. An anchored set-partition dynamic program combines disjoint subsets to cover all customers with at most K vehicles. Running the partition DP once with F costs and once with tour costs gives the clustering optimum and CVRP optimum. These references evaluate quality and do not replace failed quantum choices.

The anchor removes permutations of identical vehicle labels. Count unique partitions as sets of customer groups. S instances are independently cross-checked by brute-force assignments and constrained CPLEX. Solver settings are recorded. The references are classical computation and must not be credited to the quantum part.

## 9. How to interpret the metrics

A gap is 100*(observed/reference - 1) for feasible outputs. A missing feasible answer has undefined gap. A zero gap against a proven optimum certifies the observed solution's optimality, not a general guarantee that future runs will find it.

Model gap compares the selected F against minimum feasible F. CVRP gap routes selected clusters exactly and compares with global CVRP. Routing gap compares measured quantum tours with exact tours on those same eligible nontrivial clusters. End-to-end gap compares the actual merged plan with global CVRP. Decomposition gap routes a model-optimal grouping exactly and compares with global CVRP.

Define C_ref as global optimum, C_model as an exactly routed model-optimal grouping, C_shot as exactly routed selected shot groups and C_end as actual final tours. Then:

C_end-C_ref = (C_model-C_ref) + (C_shot-C_model) + (C_end-C_shot).

These terms isolate model/decomposition loss, grouping-search loss and routing-sampling loss. Grouping-search loss can be negative because improving F and improving travel cost are different objectives.

Best-of-batch success, raw per-shot feasibility, conditional route-hit probability and unconditional full-problem success are different quantities. Multiplying conditional tour hit rates for a fixed grouping does not measure overall CVRP success or best-of-2000 success. Invalid bitstrings remain in raw denominators. Trivial/fallback tours contribute distance but do not inflate quantum routing metrics.

## 10. Results we actually have

Formal benchmark: S/M/L x seeds 11/29 x uniform/heterogeneous demands = 12 instances. Five pipeline variants produce 60 rows. Edge/global and edge/DMM return full feasible pipelines on 11/12 instances; each succeeds on all 15 attempted four-customer routing clusters. The missing case is a clustering failure, not an edge-routing failure. Position/DMM returns full pipelines on 5/12 instances and valid routes on 8/15 four-customer routing clusters. Failures remain in the results.

The random valid-permutation baseline is strong: four customers have only 12 undirected tours, so a large random batch frequently includes the exact best one. The work must be evaluated on encoding, physical fit and transparent measurement/feasibility evidence, not on unsupported claims that quantum sampling beats classical solvers.

Separate parameter tuning: 16 candidates plus baseline, four training cases and six held-out cases. The selected settings improve mean best model gap from 8.41% to 7.57% and mean feasible trajectory rate from 58.85% to 60.42%. Solver time increases from 18.59 to 43.42 seconds, and backend calls from 126 to 153. This is a small pilot with unequal total calls, not a universal or equal-budget improvement.

Separate planetary optimization: first the plan cost 517.932168 su. Even exact routing of those groups costs 498.208382, so most loss comes from grouping. Four seeded window orders, 512 trajectories and 16000 routing shots per ship find measured tours totaling 428.127519, equal to the exact CVRP optimum on that fixed instance. There are 334 feasible trajectories; clustering uses 201000 measured shots and routing 48000. The final run takes about 23.57 CPU seconds including reference evaluation, with additional preliminary diagnostic effort excluded. This is a larger-budget instance-specific success.

## 11. What each team member should be able to explain

Explain one atom's meaning in each encoding; expand a squared penalty using x^2=x; derive the slack bit count; distinguish capacity <=Q from load=Q; explain why no slack does not imply automatic feasibility; explain the window and remaining-load check; explain why geometric coupling fit is imperfect; explain Omega versus delta; derive the edge degree penalty's linear/pair terms; give a disconnected-cycle counterexample; interpret each gap; and identify every classical contribution.

If asked whether the algorithm is optimal, answer that it is a heuristic. One measured demo solution is independently certified globally optimal. If asked whether it runs on hardware, answer CPU emulation. If asked whether all routing is quantum, distinguish the formal benchmark's trivial/fallback policy from the all-quantum-sampled planetary demo. If asked what AI did, disclose derivation assistance, coding, debugging, experiments, tests and writing; the team must still review and own every claim.

## 12. Submission and logistics

The technical package contains code, pinned dependencies, certified data, references, results, raw banks, four-page report and full mathematical write-up. The updated mathematical PDF includes current demo settings. The submission ZIP has root REPORT.pdf and MATHEMATICS.pdf aliases and a SHA-256 manifest.

Clean-environment verification details are recorded in output/submission/reproduction_check.json. Do not describe unit tests alone as a full reproduction. Competition upload, deadline, presentation format and team/contact fields depend on organizer instructions. No email or portal submission has been performed by this work.


## 13. Subsequent cloud connectivity validation

One four-atom S_11 global sequence has now returned 1000 measurements from Pasqal Cloud EMU_FREE. Its local/cloud empirical histogram total variation is 0.047. See challenge/CLOUD_SMOKE.md for the batch/job IDs, raw evidence, scope and timing caveats. This establishes a real cloud-emulator round trip, not a full cloud benchmark, DMM compatibility check or QPU execution. Do not relabel the earlier local timings as cloud timings.


## 14. M-tier cloud timing and backend limit

A subsequent M_11 cloud pilot completed 24 clustering banks and two edge-routing jobs, returning 28000 measurements. Cloud clustering took 167.04 s; the first submission to both edge results took 198.99 s with at most four workers. The 16-atom position/DMM sequence was rejected with HTTP 422 / CB1110 because the tested EMU_FREE submission path supports at most 12 atoms. Do not claim the full two-encoding suite is cloud-compatible. The pilot retains the formal classical-trivial routing policy and changes trajectory RNG consumption through stage batching. Report its outcome and timing separately from the local benchmark and the planetary demo. Full details are in challenge/CLOUD_M_PILOT.md. Additional offline cloud tests cover cache identity, the SDK BaseException error family and raw pilot evidence.
