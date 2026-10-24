# Running the Pulser Tutorial

Run from the project root:

```bash
.venv/bin/python examples/pulser_tutorial.py
```

Plots and complete measurement counts are saved in `output/pulser_tutorial/`.
This is a local, noiseless quantum-state simulation without hardware modulation response. No jobs are submitted to the cloud or a real QPU.

## Four Core Objects

- Device: defines constraints such as atom spacing, laser amplitude, and available channels.
- Register: specifies atom positions, which determine the interactions between atoms.
- Pulse: specifies laser amplitude Ω, detuning δ, phase, and duration.
- Sequence: schedules pulses on channels to describe how the system evolves over time.

QutipBackendV2 computes the evolution locally and samples the final quantum state 1000 times. In each measurement, 0 represents the ground state g and 1 represents the Rydberg excited state r. Sample counts may vary between runs.

## Example 1: A Single-Atom π Pulse

The initial state is |g⟩, and there are no interactions between atoms. On resonance and with zero phase, H/ℏ = Ωσx/2.
The excitation probability is P(r) = sin²(Ωt/2). The pulse lasts 1000 ns = 1 μs with Ω = π rad/μs, so Ωt = π and the theoretical probability is P(r) = 1.

The corresponding code is `Pulse.ConstantPulse(1000, np.pi, 0, 0)`. Its four arguments are duration (ns), amplitude (rad/μs), detuning (rad/μs), and phase (rad).
The example run produced `{'1': 1000}`.

## Example 2: A Nine-Atom Checkerboard

Nine atoms form a 3×3 square grid with a nearest-neighbor spacing of approximately 7.186761 μm.
The Hamiltonian is H/ℏ = Σᵢ[Ω(t)σxᵢ/2 − δ(t)nᵢ] + Σᵢ<ⱼ Uᵢⱼnᵢnⱼ.
Here, nᵢ is the excited-state occupation operator. Uᵢⱼ decreases with the inverse sixth power of distance, and the simulation includes interactions between all atom pairs.

Positive detuning lowers the energy of an excitation, while repulsive interactions impose an energy cost when neighboring atoms are both excited. These competing contributions favor a checkerboard arrangement.

The pulse sequence has three stages:

1. 252 ns: increase Ω from 0 to 4π while holding detuning at −12π, which favors the initial ground-state configuration.
2. 800 ns: hold Ω at 4π and sweep detuning from −12π to 4π, gradually favoring excitations.
3. 500 ns: hold positive detuning and reduce Ω to 0 to end the drive.

The total duration is 1552 ns. In register order, the target bitstring `101010101` corresponds to:

```text
1 0 1
0 1 0
1 0 1
```

The tutorial uses a finite-duration protocol inspired by adiabatic state preparation. The adiabatic theorem alone does not guarantee that this particular pulse sequence succeeds. In the first run, the target appeared in 129 of 1000 shots (12.9%), making it the most frequent individual outcome. The remaining counts were distributed across many other states. A noiseless simulation does not guarantee successful state preparation.

The connection to optimization is to encode desired solutions as low-energy states, use quantum evolution to increase the chance of measuring those solutions, and then check the sampled bitstrings classically. This example demonstrates state preparation on a fixed atom array; it does not yet encode an arbitrary optimization problem.
