"""Run both examples from Programming with Pulser using local simulation.

Run from the project root: .venv/bin/python examples/pulser_tutorial.py
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import pulser
from pulser.backends import QutipBackendV2

OUT = Path(__file__).resolve().parents[1] / 'output' / 'pulser_tutorial'
OUT.mkdir(parents=True, exist_ok=True)


def run_example(name, register, pulses):
    sequence = pulser.Sequence(register, pulser.AnalogDevice)
    sequence.declare_channel('drive', 'rydberg_global')
    for pulse in pulses:
        sequence.add(pulse, 'drive')
    print(f'Running {name}: {len(register.qubits)} atoms, {sequence.get_duration()} ns', flush=True)
    result = QutipBackendV2(sequence).run()
    counts = dict(result.final_bitstrings)
    print('Top measurements:', sorted(counts.items(), key=lambda x: -x[1])[:10], flush=True)
    # Plot the programmed input waveforms, before any hardware response.
    amplitude = np.concatenate([np.asarray(p.amplitude.samples) for p in pulses])
    detuning = np.concatenate([np.asarray(p.detuning.samples) for p in pulses])
    times = np.arange(len(amplitude)) / 1000
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(8, 5))
    axes[0].plot(times, amplitude)
    axes[0].set_ylabel('Omega (rad/us)')
    axes[1].plot(times, detuning)
    axes[1].set_ylabel('Detuning (rad/us)')
    axes[1].set_xlabel('Time (us)')
    fig.suptitle(name)
    fig.tight_layout()
    fig.savefig(OUT / f'{name}_pulses.png', dpi=160)
    plt.close(fig)
    top = sorted(counts.items(), key=lambda x: -x[1])[:15]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([x[0] for x in top], [x[1] for x in top])
    ax.set(xlabel='Measured bitstring (0=ground, 1=Rydberg)', ylabel='Shots', title=f'{name}: top measurements')
    ax.tick_params(axis='x', rotation=60)
    fig.tight_layout()
    fig.savefig(OUT / f'{name}_counts.png', dpi=160)
    plt.close(fig)
    return {'duration_ns': sequence.get_duration(), 'shots': sum(counts.values()), 'counts': counts}


def main():
    np.random.seed(42)
    one = pulser.Register.from_coordinates([(0, 0)], prefix='q')
    single = run_example('single_atom', one, [pulser.Pulse.ConstantPulse(1000, np.pi, 0, 0)])
    U = 2 * np.pi
    omega_max, delta_0, delta_f = 2 * U, -6 * U, 2 * U
    spacing = (pulser.AnalogDevice.interaction_coeff / U) ** (1 / 6)
    register = pulser.Register.square(3, spacing, prefix='q')
    sweep_ns = round((delta_f - delta_0) / (2 * np.pi * 10) * 1000)
    pulses = [
        pulser.Pulse.ConstantDetuning(pulser.RampWaveform(252, 0, omega_max), delta_0, 0),
        pulser.Pulse.ConstantAmplitude(omega_max, pulser.RampWaveform(sweep_ns, delta_0, delta_f), 0),
        pulser.Pulse.ConstantDetuning(pulser.RampWaveform(500, omega_max, 0), delta_f, 0),
    ]
    grid = run_example('nine_atom', register, pulses)
    target = '101010101'
    grid['target'] = target
    grid['target_fraction'] = grid['counts'].get(target, 0) / grid['shots']
    grid['spacing_um'] = spacing
    # Label positions by their actual register/bitstring order.
    fig, ax = plt.subplots(figsize=(5, 5))
    for i, (label, position) in enumerate(register.qubits.items()):
        x, y = np.asarray(position, dtype=float)
        ax.scatter(x, y, s=600, color='tomato' if target[i] == '1' else 'lightgray')
        ax.text(x, y, f'{label}\n{target[i]}', ha='center', va='center')
    ax.set(xlabel='x (um)', ylabel='y (um)', title='Target checkerboard: 101010101', aspect='equal')
    ax.margins(0.25)
    fig.tight_layout()
    fig.savefig(OUT / 'target_register.png', dpi=160)
    plt.close(fig)
    summary = {'single_atom': single, 'nine_atom': grid}
    (OUT / 'results.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(f'Target fraction: {grid["target_fraction"]:.1%}; spacing: {spacing:.6f} um', flush=True)
    print(f'Outputs: {OUT}', flush=True)


if __name__ == '__main__':
    main()
