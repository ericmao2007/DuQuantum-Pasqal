# Model and accounting (original Track A baseline)

## Scope

This document records the original Track A formulation. The completed Track B extension and heterogeneous-demand input support are documented in `TRACK_B_MODEL.md`; equal-demand statements below describe the original baseline family.

This is a working Track A research baseline, not a claim of quantum advantage or a completed Track B submission. It uses legal global-detuning Pulser sequences, exact local state-vector emulation of at most eight atoms, sequential reuse, and explicit rejection of infeasible measurements. It deliberately benchmarks equal-demand instances. All customer coordinates are independent uniform samples in [0,100]^2; the depot is fixed at (50,50). S/M/L use demands 3/5/6 respectively, within the prescribed ranges. The generator does not cover heterogeneous-demand CVRP.

## Formal CVRP

Let V={0,...,N}, with depot 0 and customers I=V\{0}; vehicles v=1,...,K; demand d_i; capacity Q; symmetric Euclidean costs c_ij. Let y_iv be a binary customer assignment and z_ijv a binary directed route arc for distinct i,j. Minimize sum_v sum_i!=j c_ij z_ijv subject to:

- sum_v y_iv = 1 for each customer (equality).
- sum_i d_i y_iv <= Q for each vehicle (inequality).
- sum_j!=i z_ijv = sum_j!=i z_jiv = y_iv for each customer and vehicle (equalities).
- sum_j in I z_0jv = sum_i in I z_i0v <= 1 for each vehicle (depot flow equality and trip inequality).
- sum_i,j in S,i!=j z_ijv <= |S|-1 for every nonempty customer subset S and vehicle (subtour inequalities).

Variables are binary. Unused vehicles have no arcs and zero cost. These conditions prohibit reloading and split deliveries. Euclidean costs satisfy symmetry and the triangle inequality. A certificate is still necessary: total fleet capacity alone does not establish packability.

## Constrained clustering objective

Define w_ij = EuclideanDistance(i,j)/(100 sqrt(2)), so 0 <= w_ij <= 1. For a partition G of customers into at most K groups, minimize

F(G) = sum_{S in G} [lambda |S|^2 + sum_{i<j in S} w_ij], lambda=0.15,

subject to exact coverage and sum_{i in S} d_i <= Q. The pair term encourages compact groups; the squared-size term encourages balanced cluster sizes. Lambda is fixed a priori for every instance, not fitted using reference solutions. The clustering objective omits depot travel and is not the CVRP objective. A model optimum can consequently route worse than another clustering.

## Textbook penalty and variable counts

Use x_iv for assignment and b=ceil(log2(Q+1)) binary slack bits s_vl per vehicle, with slack S_v=sum_l 2^l s_vl. An exact unconstrained penalty formulation is

F(x) + A sum_i (sum_v x_iv-1)^2 + B sum_v (sum_i d_i x_iv + S_v-Q)^2.

F(x)=lambda sum_v(sum_i x_iv)^2 + sum_v sum_i<j w_ij x_iv x_jv. With positive integer demands and binary variables, any violated integer equality contributes at least its weight. Since F>=0 and a known feasible certificate has objective U, A=B=U+1 is a sufficient (conservative) choice: a global minimizer must be feasible. This is an exact algebraic formulation, not an assertion that its coefficients can be realized by the device.

| Encoding | Formula | S | M | L | At most 80? |
|---|---|---:|---:|---:|---|
| Customer/vehicle/position | N^2 K | 32 | 300 | 900 | S only |
| Assignment without slack | NK | 8 | 30 | 60 | All |
| Assignment plus binary slack | NK+K ceil(log2(Q+1)) | 14 | 45 | 80 | All; L exactly at cap |
| Sequential customer subset, no window | N peak | 4 | 10 | 15 | All |
| Implemented sequential window | min(N,8) peak | 4 | 8 | 8 | All |

The last row is a different heuristic, not an equivalent smaller encoding. It spends repeated preparations and quantum calls instead of simultaneous atoms. `backend_calls` and `backend_shots` account for this tradeoff. The final vehicle is assigned the remainder classically without optimizing it.

## Implemented unconstrained subproblem

With R remaining customers and L vehicles remaining, take the first eight remaining customers from a seeded random ordering. This ordering uses neither geometry-based optimization nor the feasibility certificate. Let s_i indicate selecting pool customer i for the next vehicle. Choose mu=2 lambda |R|/L. The desired device cost is

E_target(s) = scale [lambda (sum_i s_i)^2 + sum_i<j w_ij s_i s_j - mu sum_i s_i], scale=4 rad/us.

Thus every linear coefficient is scale(lambda-mu) and every pair coefficient is J_ij=scale(2lambda+w_ij)>0. This is compatible with the sign and shared-linear-term restrictions in principle. Arbitrary positive J matrices still need not be distance-embeddable in two dimensions.

The reward mu targets the remaining average group size; it is not a rigorous capacity penalty. Group choices are sequential and greedy, with no backtracking or classical optimization. Each full trajectory uses one sampled subset per stage; a failed trajectory is rejected rather than repaired. The algorithm does not use reference solutions or certificate labels.

Equal demands d reduce capacity to a cardinality bound B=floor(Q/d). A selected subset S is accepted only if |S|<=B and |R|-|S|<=(L-1)B. These checks are necessary and sufficient for existence of some completion in this equal-demand family. They do not ensure that later stochastic choices succeed. Empty vehicles are allowed. Remaining customers are assigned to the final vehicle only if their load fits. No local search, exact solver, or certificate fallback supplies a missing quantum choice.

## Embedding and native energy

At zero final drive the native cost is E_phys(s)=-delta_f sum_i s_i + sum_i<j (C6/hbar)/r_ij^6 s_i s_j. Only the shared linear coefficient is controlled by global detuning; pairwise coefficients are linked through planar positions. C6/hbar is fixed. Negative, independently tunable, or exactly zero pair couplings are unavailable.

Set delta_f=scale(mu-lambda), and fit coordinates with SLSQP to minimize mean squared coupling residual, normalized by the mean target coupling squared. The optimizer has 120 iterations and ftol=1e-7. Enforce separation >=5.001 um and radius <=37.999 um. Reject an illegal or worse fit in favor of the legal grid initialization. Pulser validates every actual register and pulse. Report error = ||J_real-J_target||_2/||J_target||_2 over unordered pairs; the fitted objective and reported norm differ only by a constant normalization for a fixed target. All long-range pair interactions are retained in emulation. A graph cutoff is not used.

## Pulses and execution

Both pulses ramp Omega from 0 to 6 rad/us at delta=-12 rad/us, sweep delta linearly to delta_f at constant Omega, then ramp Omega to zero. Fast rise/sweep/fall durations are 400/1200/400 ns; slow durations are 800/3600/800 ns. Total durations 2000/5200 ns fit the 6000 ns envelope and the 4 ns clock. No DMM, noise, or modulation response is enabled. Emulation uses QutipBackendV2; no MPS bond truncation is involved. `mimic_qpu=False`: no calibrated trap layout or cloud/QPU submission is claimed.

## Evaluation and sampling semantics

For each distinct conditional register/detuning, simulate once and sample a bank of 1000 bitstrings. Reuse that finite bank as an empirical conditional distribution when drawing 32 full sequential trajectories. Report trajectory feasibility and model-reference probability over all 32 attempts, with failures retained in the denominator. These are empirical multi-call pipeline metrics, not the raw single-register feasibility rate; the separate `raw_stage_feasibility_rate` reports the latter. Cached-bank trajectories share finite-bank estimation uncertainty and are not 32 independent physical experiments. Backend shot counts are separate from trajectory counts. No confidence intervals or claims of statistical significance are made.

Among feasible trajectories choose the lowest clustering cost, breaking ties by exact routed length for evaluation only. Compute model gap against the exact constrained clustering optimum. Compute CVRP gap from the best exact-routed feasible trajectory, selected independently of the best-model trajectory. Also retain the model-selected CVRP gap to expose disagreement between objectives. Report reference-reach probabilities at both levels. No feasible trajectory means undefined gap (empty CSV field), never zero. Reference reach uses epsilon=0.000001 percent. Identical vehicle labels are canonicalized as sorted sets of sorted groups.

Uniform random bits use the same window, look-ahead, attempt budget, and rejection policy. This tests the quantum proposal mechanism; reference computations never enter either pipeline. Quantum methods spend additional bank shots and simulation work, so equal trajectory counts do not imply equal computational cost.

## Exact references

Enumerate every capacity-feasible customer subset. Compute each subset's depot tour exactly with Held-Karp subset dynamic programming (the historical Track A run used exhaustive permutations). Solve exact set partitioning by dynamic programming, anchoring the smallest remaining customer to avoid vehicle-label duplication and allowing fewer than K nonempty groups. Use separate subset costs for model and CVRP optima. Count all optimal unlabeled partitions. These expensive offline computations are evaluation only.

On S, independently enumerate all K^N assignments and cross-check both optima. Also solve both constrained set-partition models with the direct CPLEX Python API (30-second limit, one thread, zero relative MIP gap); assert agreement with exhaustive optima. CPLEX reference status is recorded separately. Larger references are proven by exhaustive subset/partition DP, not weak heuristics.

## Literature and AI use

The textbook squared-equality construction follows the general QUBO/Ising methodology in Andrew Lucas, *Ising formulations of many NP problems*, Frontiers in Physics 2 (2014), DOI: https://doi.org/10.3389/fphy.2014.00005 . It does not imply that the resulting couplings fit analog hardware. The implemented alternative avoids slack by changing the subproblem and explicitly postselecting, rather than claiming a new exact inequality penalty. Pulser is the executable source of device constraints: https://github.com/pasqal-io/Pulser .

AI assisted the derivation, code, documentation, debugging, and report. The submitted run includes executable independent reference checks and saved sequence/measurement evidence. Team members still need to review and be able to explain the model. No quantum advantage is claimed.
