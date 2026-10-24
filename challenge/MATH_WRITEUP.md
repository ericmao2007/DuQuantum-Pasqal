# Mathematical write-up: CVRP, quantum clustering, and routing

This is the comprehensive mathematical companion to the submission. It is separate from the four-page report. It describes the implemented heuristic, its exact target formulations, and its physical approximations; it does not claim that these are interchangeable. Official benchmark geometry is two-dimensional. The fictional three-dimensional planet example is an additional demonstration, not an official instance tier.

## 1. Notation and original CVRP

Let customers be $I=\{1,\ldots,N\}$, vehicles $\mathcal K=\{1,\ldots,K\}$, depot $0$, and $V=I\cup\{0\}$. Customer $i$ has location $p_i$, positive integer demand $d_i$, and each vehicle has capacity $Q$. Let

$$c_{ij}=\|p_i-p_j\|_2.$$

The depot is fixed; costs are symmetric and satisfy the triangle inequality. Customers are served once without split deliveries; a used vehicle makes one depot-to-depot trip, without reloading. Vehicles may be unused.

Use binary variables $y_{ik}$ for customer assignment and $z_{ijk}$ for a directed route edge from $i$ to $j$, $i\ne j$. The objective is

$$\min C=\sum_{k\in\mathcal K}\sum_{i\in V}\sum_{j\in V\setminus\{i\}}c_{ij}z_{ijk}.$$

Constraints are:

$$\sum_k y_{ik}=1\quad(i\in I), \tag{coverage equality}$$

$$\sum_i d_i y_{ik}\le Q\quad(k\in\mathcal K), \tag{capacity inequality}$$

$$\sum_{j\in V\setminus\{i\}}z_{ijk}=y_{ik},\qquad
\sum_{j\in V\setminus\{i\}}z_{jik}=y_{ik}\quad(i\in I,k\in\mathcal K),$$

$$\sum_{j\in I}z_{0jk}=\sum_{i\in I}z_{i0k}\le1\quad(k\in\mathcal K),$$

$$\sum_{i\in S}\sum_{j\in S\setminus\{i\}}z_{ijk}\le |S|-1
\quad(\varnothing\ne S\subseteq I,k\in\mathcal K).$$

The customer-degree equations enforce one arrival and departure for each assigned customer. Depot balance and the departure bound enforce at most one trip. Subtour inequalities exclude closed cycles that never connect to the depot. These are a formal problem statement, not all variables used by our atom encoding.

## 2. Decomposition and its approximation

For a capacity-feasible partition $\mathcal G=\{S_1,\ldots,S_m\}$ with $m\le K$, let $L^*(S)$ be the exact shortest depot tour through $S$. Then the original problem can be written

$$C^*=\min_{\mathcal G\text{ feasible}}\sum_{S\in\mathcal G}L^*(S).$$

Track A instead minimizes a chosen clustering surrogate $F(\mathcal G)$. Track B subsequently routes each fixed group. In general,

$$\arg\min F(\mathcal G)\ne\arg\min\sum_S L^*(S).$$

Thus an exact solution of the clustering model followed by exact TSP need not solve CVRP. This is decomposition error; improving a clustering score alone does not guarantee lower tour length.

## 3. Distance normalization and clustering objective

For the official square of side 100, define $D_2=100\sqrt2$ and

$$w_{ij}=c_{ij}/D_2\in[0,1].$$

Only the separate 3D demo uses $D_3=100\sqrt3$ and XYZ Euclidean distances. These normalizers keep optimization coefficients dimensionless. Reported route lengths always use original distance units, not normalized values.

Our constrained clustering objective is

$$F(\mathcal G)=\sum_{S\in\mathcal G}
\left[\lambda |S|^2+\sum_{\substack{i<j\\i,j\in S}}w_{ij}\right],
\qquad\lambda=0.15.$$

The first term favors balanced group sizes: if group sizes differ by more than one and a transfer is feasible, moving one customer from the larger to the smaller reduces the sum of squares. The pair term penalizes geographically dispersed groups. This objective omits depot travel and tour ordering.

With binary assignment variables $x_{ik}$ the same objective is

$$F(x)=\lambda\sum_k\left(\sum_i x_{ik}\right)^2
+\sum_k\sum_{i<j}w_{ij}x_{ik}x_{jk},$$

subject to $\sum_kx_{ik}=1$ and $\sum_i d_ix_{ik}\le Q$.

## 4. Canonical QUBO convention

We use

$$E(b)=c_0+\sum_a h_ab_a+\sum_{a<b}J_{ab}b_ab_b,\qquad b_a\in\{0,1\}.$$

Because $b_a^2=b_a$, squares remain quadratic. For a symmetric matrix representation $b^T\mathbf Qb$, set

$$\mathbf Q_{aa}=h_a,\qquad \mathbf Q_{ab}=\mathbf Q_{ba}=J_{ab}/2\ (a\ne b).$$

The factor of two is essential: both symmetric matrix entries contribute to a cross term. The constant $c_0$ does not change the optimizer. A positive overall scale also preserves minimizers; changing individual coefficients generally does not.

## 5. Textbook exact penalties with binary slack

An equality $g(b)=0$ can be penalized by $A g(b)^2$. An inequality cannot generally be replaced by $(\mathrm{load}-Q)^2$: that would penalize valid underfilled vehicles.

Introduce integer slack $s_k\ge0$ so

$$\sum_i d_ix_{ik}+s_k=Q.$$

Let $B_Q=\lceil\log_2(Q+1)\rceil$, $a_\ell=2^\ell$, and

$$s_k=\sum_{\ell=0}^{B_Q-1}a_\ell u_{k\ell},\qquad u_{k\ell}\in\{0,1\}.$$

The binary register can represent every slack in $0,\ldots,Q$. Extra representable slack values above $Q$ cannot give zero residual when load is nonnegative. An exact algebraic formulation is

$$E_{\rm slack}=F(x)+A\sum_i\left(\sum_kx_{ik}-1\right)^2
+B\sum_k\left(\sum_id_ix_{ik}+\sum_\ell a_\ell u_{k\ell}-Q\right)^2.$$

For example,

$$\left(\sum_kx_{ik}-1\right)^2
=1-\sum_kx_{ik}+2\sum_{k<r}x_{ik}x_{ir}.$$

For one vehicle, capacity expansion gives

$$Q^2+\sum_i(d_i^2-2Qd_i)x_{ik}
+2\sum_{i<j}d_id_jx_{ik}x_{jk}
+\sum_\ell(a_\ell^2-2Qa_\ell)u_{k\ell}
+2\sum_{\ell<m}a_\ell a_m u_{k\ell}u_{km}
+2\sum_{i,\ell}d_i a_\ell x_{ik}u_{k\ell}.$$

Consequently the assignment linear coefficient is

$$h_{ik}=\lambda-A+B(d_i^2-2Qd_i),$$

same-vehicle customer couplings are $2\lambda+w_{ij}+2Bd_id_j$, different-vehicle copies of the same customer couple with $2A$, and assignment/slack couplings are $2Bd_ia_\ell$. The constant is $AN+BKQ^2$.

### A sufficient penalty bound

Let $U=F(x^{\rm cert})$ for a checked feasible certificate. Set $A=B=U+1$. Since $F\ge0$ even outside the feasible set, any violated integer equality incurs energy at least $U+1$, while the certificate with matching slack has energy $U$. Thus every global minimizer is feasible. This is conservative and is an algebraic statement: the resulting coefficient magnitudes, nonuniform linear terms, and dense interactions need not fit analog hardware.

## 6. Variable accounting

| Encoding | Count | S: N=4,K=2,Q=7 | M: N=10,K=3,Q=20 | L: N=15,K=4,Q=30 |
|---|---|---:|---:|---:|
| Direct customer/vehicle/position | $N^2K$ | 32 | 300 | 900 |
| Assignment only | $NK$ | 8 | 30 | 60 |
| Assignment plus slack | $NK+K\lceil\log_2(Q+1)\rceil$ | 14 | 45 | 80 |
| Sequential subsets, no window | peak $N$ | 4 | 10 | 15 |
| Implemented eight-customer window | peak $\min(N,8)$ | 4 | 8 | 8 |

The 80-atom cap is met by all assignment/slack cases, but L exactly exhausts it. The sequential rows are different heuristics, not equivalent exact compressed encodings. They trade peak atoms for repeated preparation, restricted choices, and rejection. Quantum routing adds a separate peak of 10 or 16 atoms, reused across clusters, rather than simultaneous clustering-plus-routing registers.

## 7. Implemented slack-free sequential subproblem

Let $R$ be unassigned customers, $L$ remaining vehicles, and $W\subseteq R$ a window of at most eight customers from a seeded random ordering. Use $b_i=1$ if pool customer $i$ joins the current vehicle. Define

$$\mu=2\lambda|R|/L,$$

$$E_{\rm target}(b)=\kappa_A\left[
\lambda\left(\sum_{i\in W}b_i\right)^2
+\sum_{i<j\in W}w_{ij}b_ib_j-\mu\sum_{i\in W}b_i\right],
\qquad\kappa_A=4.$$

Ignoring pair distances and treating $m=\sum_i b_i$ as continuous, $\lambda m^2-\mu m$ is minimized at $m=\mu/(2\lambda)=|R|/L$. This motivates the reward; it does not guarantee the target size or capacity. Expanding gives

$$h_i^{\rm tar}=\kappa_A(\lambda-\mu),\qquad
J_{ij}^{\rm tar}=\kappa_A(2\lambda+w_{ij})>0.$$

All linear coefficients are shared, and pair coefficients have the available sign. This helps compatibility but does not establish geometric embeddability.

### What enforces feasibility in the actual code?

After measuring subset $S$, the code checks

$$\sum_{i\in S}d_i\le Q,\qquad
\sum_{i\in R\setminus S}d_i\le(L-1)Q.$$

A failed check rejects the trajectory. Customers are removed once assigned, so duplicates cannot occur; full coverage and the final vehicle load are checked before accepting a complete plan. The last vehicle receives the remainder. No exact reference or certificate repairs a failed measured assignment.

The remaining-load bound is only necessary under heterogeneous demands. For example, three customers of demand 2 cannot fit two vehicles of capacity 3 although their total demand equals total capacity.

With equal demand $d$, a stronger exact completion-existence check is

$$|S|\le\lfloor Q/d\rfloor,\qquad
|R\setminus S|\le(L-1)\lfloor Q/d\rfloor.$$

The implementation uses actual load sums. The two tests agree for the reported uniform S/M/L cases, but should not be claimed equivalent for every equal-demand parameter choice. In particular, summing unused capacity across several vehicles can hide integer packing losses.

This method avoids slack by changing the subproblem and postselecting, not by deriving an exact smaller capacity QUBO. The window and sequential decisions can exclude globally desirable partitions.

## 8. Native Rydberg Hamiltonian and energy mapping

Let $n_a=|r\rangle\langle r|_a$ and $X_a=|g\rangle\langle r|_a+|r\rangle\langle g|_a$. To avoid unit ambiguity, define

$$\Gamma=C_6^{\rm physical}/\hbar
=\texttt{device.interaction\_coeff}\approx865723.02\;
\mathrm{rad}\,\mu\mathrm{s}^{-1}\,\mu\mathrm{m}^6.$$

For planar atom positions $r_a$, the real-phase global drive is

$$\frac{H(t)}{\hbar}=\frac{\Omega(t)}2\sum_aX_a
-\delta(t)\sum_an_a
+\sum_{a<b}\frac{\Gamma}{\|r_a-r_b\|^6}n_an_b.$$

At final $\Omega(T)=0$, a bitstring has diagonal angular-frequency cost

$$\mathcal E_{\rm phys}(b)=-\delta_f\sum_ab_a
+\sum_{a<b}\frac{\Gamma}{\|r_a-r_b\|^6}b_ab_b.$$

To match a dimensionless QUBO with positive scale $\kappa$, one would need

$$-\delta_{a,f}=\kappa h_a,\qquad
\Gamma/\|r_a-r_b\|^6=\kappa J_{ab}.$$

These are targets, not independently programmable settings. The coefficients in Section 7 already include their scale and must not be scaled twice. Global detuning gives one shared linear coefficient; geometry links all couplings. Native pair couplings are positive and cannot be exactly zero at finite separation. Three-dimensional customer coordinates do not imply three-dimensional physical atom placement.

## 9. Embedding objective and errors

For already scaled target $J_{ab}^{\rm tar}$, let $M=m(m-1)/2$, $\bar J=M^{-1}\sum_{a<b}J_{ab}^{\rm tar}$, and $J_{ab}^{\rm real}=\Gamma/\|r_a-r_b\|^6$. The code fits

$$\min_{r_1,\ldots,r_m\in\mathbb R^2}
\frac1M\sum_{a<b}\left(\frac{J_{ab}^{\rm real}-J_{ab}^{\rm tar}}{\bar J}\right)^2$$

subject to separation at least 5.001 micrometers and radius at most 37.999 micrometers. It uses SLSQP, at most 120 iterations, and ftol $10^{-7}$. An illegal or worse fit falls back to the legal initial grid. This is a local numerical fit, not a proven globally optimal embedding.

Report

$$\epsilon_J=\frac{\sqrt{\sum_{a<b}(J_{ab}^{\rm real}-J_{ab}^{\rm tar})^2}}
{\sqrt{\sum_{a<b}(J_{ab}^{\rm tar})^2}}.$$

Desired zeros still contribute unwanted physical couplings in the numerator. The one-atom case has no pairwise fitting problem. A small coefficient error does not by itself prove that the minimizing bitstring or state ranking is preserved.

For global-only nonuniform linear terms, the least-squares projection is

$$h_a^{\rm real}=\bar h=\frac1m\sum_a h_a,\qquad
\epsilon_h=\|h^{\rm real}-h\|_2/\|h\|_2.$$

It can discard much of a route's cost information, especially in the edge encoding.

## 10. Emulator-only DMM linear mapping

With local weight $\varepsilon_a\in[0,1]$ and $\delta_{\rm DMM}\le0$,

$$h_a^{\rm real}=-\delta_{\rm global}-\varepsilon_a\delta_{\rm DMM}.$$

For scaled target $h$, set $h_{\min}=\min_a h_a$ and $D=\max_a h_a-h_{\min}$. Choose

$$\delta_{\rm global}=-h_{\min},\qquad
\delta_{\rm DMM}=-D,\qquad
\varepsilon_a=(h_a-h_{\min})/D.$$

Then $h_a^{\rm real}=h_a$. If $D=0$, use zero DMM and zero weights. This raises selected excitation costs relative to the common minimum, which has the allowed sign. Exact matching additionally requires the chosen global detuning, DMM range, and total weighted detuning to obey the declared control bounds. Our DMM is an explicitly added emulation control, not evidence that this control is available in a QPU submission.

## 11. Pulses, evolution, and measurement

State evolution obeys

$$i\,\partial_t|\psi(t)\rangle=(H(t)/\hbar)|\psi(t)\rangle.$$

For $t_1$ rise, $t_2$ sweep, and $t_3$ fall, with $T=t_1+t_2+t_3$,

$$\Omega(t)=\begin{cases}
\Omega_{\max}t/t_1,&0\le t<t_1,\\
\Omega_{\max},&t_1\le t<t_1+t_2,\\
\Omega_{\max}(T-t)/t_3,&t_1+t_2\le t\le T,
\end{cases}$$

$$\delta(t)=\begin{cases}
\delta_0,&0\le t<t_1,\\
\delta_0+(\delta_f-\delta_0)(t-t_1)/t_2,&t_1\le t<t_1+t_2,\\
\delta_f,&t_1+t_2\le t\le T.
\end{cases}$$

The code uses $\Omega_{\max}=6$ rad/microsecond and $\delta_0=-12$ rad/microsecond. Clustering has fast 400/1200/400 ns and slow 800/3600/800 ns schedules. Routing uses the slow schedule. Thus total times are 2000 and 5200 ns, within 6000 ns and the 4 ns clock. At $t=0$, zero drive and negative detuning make the all-ground state the ground state of the positive-interaction model.

The adiabatic idea requires slow change relative to spectral gaps. A useful diagnostic scale is $|\langle 1|\partial_t(H/\hbar)|0\rangle|/(\omega_1-\omega_0)^2$, away from degeneracies. We do not verify an adiabatic guarantee. Finite duration can leave excited-state amplitudes even without noise; slow evolution of an incorrectly embedded target would still optimize the wrong native energy.

If $|\psi(T)\rangle=\sum_b\alpha_b|b\rangle$, then

$$p(b)=|\alpha_b|^2,\qquad\widehat p(b)=N_b/N_{\rm shots}.$$

An occupation curve displays $\langle n_a(t)\rangle$, not a definite route during evolution. Zero observed counts do not establish zero underlying probability.

The 5.2 microsecond pulse duration is not end-to-end solver wall time. Embedding, many shots, preparation/readout on real hardware, classical checks, and fallback work are distinct costs. Current experiments time a CPU emulator, not a real QPU.

## 12. TSP position encoding

For a fixed group of $n$ customers, use $x_{it}=1$ when local customer $i$ occupies position $t\in\{0,\ldots,n-1\}$. The depot stays outside these positions. With normalized travel costs $\widetilde c_{ij}$, minimize

$$E_{\rm pos}=\sum_i\widetilde c_{0i}x_{i0}
+\sum_i\widetilde c_{i0}x_{i,n-1}
+\sum_{t=0}^{n-2}\sum_{i\ne j}\widetilde c_{ij}x_{it}x_{j,t+1}
+A_{\rm TSP}\sum_i\left(\sum_t x_{it}-1\right)^2
+A_{\rm TSP}\sum_t\left(\sum_i x_{it}-1\right)^2.$$

The row and column constraints mean every customer appears once and each position has one customer. There are $n^2$ variables. Its constant is $2nA_{\rm TSP}$ and

$$h_{it}=-2A_{\rm TSP}+\widetilde c_{0i}\mathbf1_{t=0}
+\widetilde c_{i0}\mathbf1_{t=n-1}.$$

Variables sharing a customer or position couple with $2A_{\rm TSP}$; consecutive-position travel contributes positive additional pair terms. Only permutation matrices are decoded. For $n=4$, 16 atoms represent 24 directed orderings, or 12 tours after reversal symmetry.

## 13. TSP undirected-edge encoding and its restricted validity

Let $e_{ij}$ indicate selecting unordered edge $\{i,j\}$ among the depot and $n$ customers. Use

$$E_{\rm edge}=\sum_{i<j}\widetilde c_{ij}e_{ij}
+A_{\rm TSP}\sum_{v=0}^{n}\left(\sum_{e\ni v}e-2\right)^2.$$

For a vertex degree $D_v$,

$$ (D_v-2)^2=4-3\sum_{e\ni v}e
+2\sum_{\substack{e<f\\e,f\ni v}}ef.$$

Each edge touches two vertices, so its linear coefficient is $\widetilde c_{ij}-6A_{\rm TSP}$. Edge pairs sharing a vertex couple with $2A_{\rm TSP}$; disjoint edge pairs have zero target coupling. The constant is $4(n+1)A_{\rm TSP}$, and variable count is

$$\binom{n+1}{2}=n(n+1)/2.$$

Degree two implies a disjoint union of cycles, not generally one connected tour. For **2 through 4 customers**, there are 3 through 5 vertices; two disjoint simple cycles would require at least six vertices, so degree two is sufficient. For $n\ge5$, it is not: two triangles are a counterexample at six vertices. For one customer, the depot trip traverses the same undirected edge twice and is handled classically, not by this binary simple-cycle model.

Only four-customer nontrivial clusters are quantum-routed in our implementation. Larger groups receive declared classical size fallback; failed four-customer batches are not repaired. Position encoding is also capped at four customers for execution. At four customers the comparison is 16 versus 10 atoms.

### TSP penalty choice

Set $A_{\rm TSP}=10$. With normalized costs in $[0,1]$, a valid four-customer tour costs at most five. All travel contributions are nonnegative, and any violated squared integer constraint adds at least ten. Therefore no invalid bitstring can be a global minimum of either exact target QUBO. This guarantee does not survive arbitrary embedding distortion automatically. Routing scales the entire QUBO by $\kappa_B=0.1$ before physical mapping; the target optimizer is unchanged.

Tests enumerate all $2^{10}=1024$ edge bitstrings and $2^{16}=65536$ position bitstrings, finding 12 and 24 valid states. Each valid target energy equals normalized tour length. This checks algebra, not analog success probability.

## 14. Exact references and classical dynamic programming

Let $D(S,j)$ be the shortest depot-starting path through exactly customer subset $S$ and ending at $j\in S$. Held-Karp uses

$$D(\{j\},j)=c_{0j},\qquad
D(S,j)=\min_{i\in S\setminus\{j\}}[D(S\setminus\{j\},i)+c_{ij}],$$

$$L^*(S)=\min_{j\in S}[D(S,j)+c_{j0}].$$

Only capacity-feasible subsets need be considered, since positive demands make their subsets feasible as well. For a subset cost $f(S)$, define the anchored partition recurrence

$$V(R,L)=\min_{\substack{S\subseteq R,\ \min R\in S\\\sum_{i\in S}d_i\le Q}}
[f(S)+V(R\setminus S,L-1)].$$

Boundary values are $V(\varnothing,L)=0$ and $V(R,0)=+\infty$ for nonempty $R$. Taking $f=L^*$ gives the exact CVRP reference; taking $f(S)=\lambda |S|^2+\sum_{i<j\in S}w_{ij}$ gives the exact clustering reference. Anchoring removes vehicle-label permutations and still allows unused vehicles. Count all tied optimal unlabeled partitions; choose one representative when routing a tied model optimum and disclose the tie policy.

S instances are independently checked by enumerating assignments and by constrained CPLEX set partitioning. CPLEX uses 30 seconds, one thread, and zero relative MIP gap. Exact references are offline evaluation; they must not be credited as quantum computation. In the submitted benchmark, precomputed exact tours are also used for explicitly classical trivial/size-fallback routes; the independent timing comparison computes those fallback routes inside its online timer.

## 15. Feasible-instance certificates and ratios

A certificate $a:I\to\mathcal K$ is checked by

$$\forall k:\sum_{i:a(i)=k}d_i\le Q.$$

Our generators construct a cyclic certificate. The heterogeneous generator reduces the largest demands within certificate groups until they fit, while retaining positive integer demands within tier limits. Certificate existence proves feasibility, but certificate labels are never used by the quantum sampler.

Report

$$\rho=\frac{\sum_i d_i}{KQ},\qquad\eta=\frac{\max_i d_i}{Q}.$$

If a solution uses $m$ nonempty groups, its equivalent vehicle labelings number $K!/(K-m)!$. Compare canonical sets of customer groups instead of counting these relabelings as different solutions.

## 16. Gaps and the three-loss identity

Let $F^*$ be the exact constrained model optimum; $\mathcal G_F^*$ a chosen model-optimal partition; $\widehat{\mathcal G}$ the selected feasible measured partition; and

$$C_{\rm ref}=C^*,\quad C_{\rm model}=\sum_{S\in\mathcal G_F^*}L^*(S),\quad
C_{\rm shot}=\sum_{S\in\widehat{\mathcal G}}L^*(S),\quad
C_{\rm end}=\sum_{S\in\widehat{\mathcal G}}\widehat L(S).$$

For positive reference $B$, use $g(A;B)=100(A-B)/B$. If a denominator is zero, report an appropriate absolute difference rather than divide by zero.

| Metric | Formula |
|---|---|
| Model gap | $g(F(\widehat{\mathcal G});F^*)$ |
| CVRP gap | $g(C_{\rm shot};C_{\rm ref})$ |
| End-to-end gap | $g(C_{\rm end};C_{\rm ref})$ |
| Decomposition gap | $g(C_{\rm model};C_{\rm ref})$ |
| Routing gap | $g(\sum_{S\in\mathcal Q}\widehat L(S);\sum_{S\in\mathcal Q}L^*(S))$ |

Here $\mathcal Q$ contains eligible nontrivial quantum-routed clusters only; trivial and classical size-fallback clusters do not enter routing gap. A failed eligible quantum batch makes the aggregate routing/end-to-end result undefined; it is not silently omitted from a success-only average.

In absolute distance units,

$$C_{\rm end}-C_{\rm ref}
=\underbrace{C_{\rm model}-C_{\rm ref}}_{\text{decomposition loss}}
+\underbrace{C_{\rm shot}-C_{\rm model}}_{\text{clustering loss}}
+\underbrace{C_{\rm end}-C_{\rm shot}}_{\text{routing loss}}.$$

This is an exact telescoping identity for one consistent selected clustering, not a sum of percentages with different denominators. Clustering loss may be negative because model score and route length are different objectives. Relative gaps can also be negative against a merely best-known reference; do not clip them.

Track A saves both best-model and best-exact-routed sampled clusterings. Their gaps need not select the same shot. Track B's loss identity uses its fixed best-model selected clustering consistently.

## 17. Feasibility, reference reach, and sampling scope

For $M$ full trajectories,

$$\widehat P_{\rm feasible}=\frac{\#\{\text{fully feasible trajectories}\}}M,$$

$$\widehat P_{\rm ref}=\frac{\#\{\text{feasible trajectories with gap}\le\epsilon\}}M.$$

Failures stay in the denominator. The chosen tolerance is $\epsilon=10^{-6}$ percent, equivalent to cost ratio $\le1+10^{-8}$ for positive references. Conditional stage-shot feasibility and full-trajectory feasibility are different quantities.

For a routing histogram with counts $N_b$,

$$\widehat p_{\rm valid}=\frac{\sum_{b\text{ valid}}N_b}{N_{\rm shots}},\qquad
\widehat p_{\rm hit}=\frac{\sum_{b\text{ valid},\ \mathrm{gap}(b)\le\epsilon}N_b}{N_{\rm shots}}.$$

Under independent route draws for fixed clusters, their reference-hit probabilities multiply. This is conditional on the chosen clustering, not an unconditional full-CVRP success probability. For independent, identically distributed trials with success probability $p$, best-of-$M$ success is $1-(1-p)^M$; shared finite banks, adaptive choices, and best-clustering selection require care before using that formula.

Our conditional clustering banks contain 1000 measured bitstrings per distinct register/detuning. Benchmark trajectories resample from these finite empirical distributions; they share bank-estimation uncertainty. Official runs use 32 trajectories; the US/space demos use 64. Routing uses 2000 shots per eligible cluster. Multiple counts of one tour are distinct shots, not distinct candidate tours.

## 18. Optional background: single-atom pulses, blockade, and Ising spins

A resonant single atom with $H/\hbar=\Omega X/2$, initially in $|g\rangle$, has

$$P(r,t)=\sin^2(\Omega t/2).$$

A constant pi pulse satisfies $\Omega T=\pi$, e.g. $T=1000$ ns $=1$ microsecond and $\Omega=\pi$ rad/microsecond. Continuing to $2\pi$ returns the ideal atom to its initial state; more drive time is not monotonically better.

For a resonant pair, interaction angular frequency $U=\Gamma/R^6$ greatly exceeding $\Omega$ suppresses double excitation. The reference blockade radius satisfies

$$R_b=(\Gamma/\Omega)^{1/6}.$$

This is a crossover scale, not a hard interaction cutoff. The symmetric singly excited state has collective Rabi frequency $\sqrt2\Omega$ in the ideal strong-blockade limit, explaining why a single-atom pulse is not a calibrated collective pi pulse.

For abstract classical spins $z_a=2b_a-1$, canonical QUBO becomes an Ising polynomial with

$$K_{ab}=J_{ab}/4,\qquad g_a=h_a/2+\tfrac14\sum_{b\ne a}J_{ab},$$

plus constant $c_0+\frac12\sum_a h_a+\frac14\sum_{a<b}J_{ab}$. This spin-sign convention must be stated; a Pauli-Z convention assigning ground state eigenvalue +1 instead uses $n=(I-Z)/2$.

## 19. Mathematical claims and scope checklist

- The original CVRP and exact penalized target QUBOs are precisely defined.
- The implemented sequential subset procedure is a heuristic with classical rejection, not an equivalent exact compression.
- Exact target feasibility does not imply faithful native embedding or successful state preparation.
- Global-only and emulator-DMM linear controls are different experimental regimes.
- The degree-only edge TSP requires its stated size restriction; one-customer trips are a separate trivial case.
- Exact references, classical fallbacks, and quantum measurements are separately credited.
- Zero feasible outcomes give undefined gaps, not zero gaps.
- The 3D fictional demo does not change the official 2D benchmark or the 2D atom register.
- Current timing evidence concerns classical CPU emulation; it establishes no real-QPU speedup.

## Sources and code correspondence

Primary task source: user-supplied *Pasqal-challenge-final.pdf*, version 3.0, updated 24 October 2026, especially Derive 2.1, 3.1, 4.1 and Tasks A1-A4/B1-B3. General squared-constraint methodology: Andrew Lucas, *Ising formulations of many NP problems*, Frontiers in Physics 2 (2014), https://doi.org/10.3389/fphy.2014.00005 . The alternative sequential method and its limitations are derived explicitly above; no novel exact encoding is claimed.

Implementation: `core.py` (distances, objective, certificates, exact references), `quantum.py` (subset QUBO and embedding), `routing.py` (TSP QUBOs, controls, decoders), `run.py` and `track_b.py` (sampling and metrics), `space_demo.py` (separate XYZ example), and the three test modules (independent algebra/reference/evidence checks). AI assisted derivation, writing, and implementation. The team must review and be able to defend every formula and claim.
