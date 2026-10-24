# Register and Rydberg Interactions

Run from the project root:

```bash
.venv/bin/python examples/register_interactions.py
```

Outputs are saved in `output/register_interactions/`. The script runs locally with an ideal noiseless QutipBackendV2 simulation and no hardware modulation response.

## Register construction

The script creates the tutorial's manually labeled 2x2 square, its centered equivalent, and a 12-atom triangular lattice. Centering translates every atom by the same vector, so pairwise distances and interactions are unchanged. Bitstrings follow `register.qubit_ids`, not an inferred spatial order.

## Interaction and blockade

In angular-frequency units, U = device.interaction_coeff / R**6, where the coefficient is C6/hbar. The interaction contributes U only when both atoms are excited. Doubling R reduces U by a factor of 64.

For a resonant drive, Rb = (device.interaction_coeff / Omega)**(1/6). Strong blockade requires U much greater than Omega, or R much smaller than Rb. This is suppression caused by an interaction-induced shift out of resonance, rather than a hard distance cutoff or an absolute energy barrier.

The tutorial calculations give:

- Omega = 1 rad/us: Rb = 9.762548 um.
- Rb = 8 um: Omega = 3.302471 rad/us.
- Triangular lattice with Rb = 7 um: 12 atoms and 23 graph edges.

The graph connects pairs separated by less than Rb. Pairs without an edge still have nonzero physical interactions. Circles have radius Rb/2 so overlapping circles indicate a separation below Rb.

## Additional two-atom experiment

The script applies the same global resonant pulse to atoms separated by 5, 10, and 20 um: duration 1000 ns, Omega = pi rad/us, zero detuning, zero phase. This is a single-atom pi pulse, not a collectively calibrated pi pulse.

One run with 1000 shots per distance gave:

| Separation | U/Omega | 00 | 01 | 10 | 11 |
|---|---:|---:|---:|---:|---:|
| 5 um | 17.6364 | 345 | 325 | 330 | 0 |
| 10 um | 0.2756 | 15 | 20 | 23 | 942 |
| 20 um | 0.0043 | 0 | 0 | 0 | 1000 |

Counts are samples, not exact probabilities. Zero observed 11 outcomes does not establish exactly zero probability.

In the strong-blockade limit, the global drive couples |gg> to the symmetric state (|gr> + |rg>)/sqrt(2) at a collective Rabi frequency sqrt(2)*Omega. Thus the 5 um case need not finish with exactly one excitation: the chosen duration is calibrated for a single atom. In the ideal strong-blockade limit, a collective pi pulse would last pi/(sqrt(2)*Omega), approximately 707 ns for this Omega, subject to device timing constraints.

## Implications for optimization

Atom positions set the pairwise penalties, while amplitude and detuning set other terms of the Hamiltonian. These must be designed together. A distance-based positive interaction matrix cannot represent arbitrary QUBO coefficients without additional modeling or embedding techniques. A blockade connectivity graph is an approximation useful for problems such as maximum independent set on suitable geometric graphs.
