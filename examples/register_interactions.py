"""Explore registers, distance-dependent interactions, and Rydberg blockade.

Run: .venv/bin/python examples/register_interactions.py
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Circle
import pulser
from pulser.backends import QutipBackendV2

OUT = Path(__file__).resolve().parents[1] / 'output' / 'register_interactions'


def coordinates(register):
    return {str(k): np.asarray(v, dtype=float).tolist() for k, v in register.qubits.items()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    np.random.seed(42)
    device = pulser.AnalogDevice
    manual = pulser.Register({'q0': [0, 0], 'q1': [5, 0], 'q2': [0, 5], 'q3': [5, 5]})
    centered = pulser.Register.from_coordinates(list(coordinates(manual).values()), prefix='q', center=True)
    print('Qubit/bitstring order:', manual.qubit_ids)
    print('Manual coordinates:', coordinates(manual))
    print('Centered coordinates:', coordinates(centered))
    rb = float(device.rydberg_blockade_radius(1))
    omega8 = float(device.rabi_from_blockade(8))
    print(f'Blockade radius at Omega=1 rad/us: {rb:.6f} um')
    print(f'Omega for blockade radius=8 um: {omega8:.6f} rad/us')
    tri = pulser.Register.triangular_lattice(rows=4, atoms_per_row=3, spacing=6, prefix='q')
    xy = np.array(list(coordinates(tri).values()))
    radius = 7.0
    fig, ax = plt.subplots(figsize=(7, 7))
    edges = 0
    for i in range(len(xy)):
        for j in range(i):
            if np.linalg.norm(xy[i] - xy[j]) < radius:
                ax.plot(*xy[[i, j]].T, color='gray', zorder=1)
                edges += 1
    for label, (x, y) in zip(tri.qubit_ids, xy):
        ax.add_patch(Circle((x, y), radius / 2, color='steelblue', alpha=0.12))
        ax.scatter(x, y, color='navy', zorder=3)
        ax.text(x + 0.3, y + 0.3, str(label))
    ax.set(xlabel='x (um)', ylabel='y (um)', title='12-atom triangular lattice: Rb = 7 um', aspect='equal')
    ax.autoscale_view()
    fig.tight_layout()
    fig.savefig(OUT / 'triangular_blockade_graph.png', dpi=160)
    plt.close(fig)

    # The smooth curve is the physical interaction; Rb is only a reference scale.
    distances = np.linspace(5, 25, 400)
    omega = np.pi
    interaction = device.interaction_coeff / distances**6
    rb_pi = float(device.rydberg_blockade_radius(omega))
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.semilogy(distances, interaction / omega)
    ax.axhline(1, color='gray', linestyle='--', label='U / Omega = 1')
    ax.axvline(rb_pi, color='tomato', linestyle='--', label=f'Rb = {rb_pi:.2f} um')
    ax.set(xlabel='Atom separation (um)', ylabel='U / Omega', title='Interaction relative to the drive (Omega = pi rad/us)')
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / 'interaction_vs_distance.png', dpi=160)
    plt.close(fig)

    # Additional experiment: identical resonant pi pulses at different separations.
    experiments = []
    for distance in [5, 10, 20]:
        register = pulser.Register.from_coordinates([(0, 0), (distance, 0)], prefix='q')
        sequence = pulser.Sequence(register, device)
        sequence.declare_channel('drive', 'rydberg_global')
        sequence.add(pulser.Pulse.ConstantPulse(1000, omega, 0, 0), 'drive')
        counts = dict(QutipBackendV2(sequence).run().final_bitstrings)
        ratio = float(device.interaction_coeff / distance**6 / omega)
        experiments.append({'distance_um': distance, 'U_over_Omega': ratio, 'counts': counts})
        print(f'R={distance} um, U/Omega={ratio:.4f}: {counts}', flush=True)
    states = ['00', '01', '10', '11']
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(3)
    for i, state in enumerate(states):
        fractions = [e['counts'].get(state, 0) / sum(e['counts'].values()) for e in experiments]
        ax.bar(x + (i - 1.5) * 0.2, fractions, width=0.2, label=state)
    ax.set_xticks(x, ['5 um', '10 um', '20 um'])
    ax.set(xlabel='Atom separation', ylabel='Measured fraction', title='Same resonant pi pulse, different atom spacing', ylim=(0, 1.05))
    ax.legend(title='Bitstring')
    fig.tight_layout()
    fig.savefig(OUT / 'two_atom_measurements.png', dpi=160)
    plt.close(fig)
    summary = {'manual_register': coordinates(manual), 'centered_register': coordinates(centered), 'blockade_radius_at_omega_1_um': rb, 'omega_for_rb_8_rad_per_us': omega8, 'triangular_graph_edges': edges, 'two_atom_experiments': experiments}
    (OUT / 'results.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(f'Triangular graph: {len(xy)} atoms, {edges} edges')
    print(f'Outputs: {OUT}')


if __name__ == '__main__':
    main()
