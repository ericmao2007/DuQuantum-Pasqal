"""Legal global-detuning embeddings and measured subset proposals."""
import time
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.distance import pdist, squareform
import pulser
from pulser.backends import QutipBackendV2
from pulser.backend import BitStrings
from pulser_simulation import QutipConfig
from .core import BALANCE

SCALE = 4.0
WINDOW = 8
BANK_SHOTS = 1000
PULSES = {'fast': (400, 1200, 400), 'slow': (800, 3600, 800)}


def embed(target):
    n = len(target)
    if n == 1:
        return np.zeros((1, 2)), 0., 0
    # Deterministic geometric starting point, independent of reference solutions.
    xy = np.array([(i % 3, i // 3) for i in range(n)], dtype=float) * 9
    xy -= xy.mean(axis=0)
    ij = np.triu_indices(n, 1)
    wanted = target[ij]
    coeff = pulser.AnalogDevice.interaction_coeff

    def loss(flat):
        r = np.maximum(pdist(flat.reshape(n, 2)), 1e-6)
        realized = coeff / r**6
        return np.mean(((realized - wanted) / np.mean(wanted))**2)

    constraints = [
        {'type': 'ineq', 'fun': lambda x: pdist(x.reshape(n, 2)) - 5.001},
        {'type': 'ineq', 'fun': lambda x: 37.999 - np.linalg.norm(x.reshape(n, 2), axis=1)},
    ]
    fit = minimize(loss, xy.ravel(), method='SLSQP', bounds=[(-37, 37)] * (2 * n),
                   constraints=constraints, options={'maxiter': 120, 'ftol': 1e-7})
    candidate = fit.x.reshape(n, 2)
    legal = np.min(pdist(candidate)) >= 5 and np.max(np.linalg.norm(candidate, axis=1)) <= 38
    if legal and loss(candidate.ravel()) < loss(xy.ravel()):
        xy = candidate
    realized = coeff / pdist(xy)**6
    error = float(np.linalg.norm(realized - wanted) / np.linalg.norm(wanted))
    return xy, error, int(fit.nit)


class Sampler:
    def __init__(self, instance, pair, pulse, seed):
        self.instance, self.pair, self.pulse = instance, pair, pulse
        self.seed = seed
        self.cache, self.embeddings, self.banks = {}, {}, []
        self.backend_seconds = 0.
        self.backend_calls = 0
        self.backend_shots = 0
        self.order = list(np.random.default_rng(instance['seed'] + 900).permutation(len(pair)))

    def pool(self, remaining):
        return tuple(i for i in self.order if i in remaining)[:WINDOW]

    def draw(self, remaining, left, rng):
        pool = self.pool(remaining)
        n = len(pool)
        target_size = len(remaining) / left
        # F(S)-mu|S|; mu adapts to the remaining mean cluster size.
        mu = 2 * BALANCE * target_size
        final_delta = SCALE * (mu - BALANCE)
        target = SCALE * (2 * BALANCE + self.pair[np.ix_(pool, pool)])
        np.fill_diagonal(target, 0)
        key = (pool, round(final_delta, 10))
        if self.pulse == 'random':
            bits = rng.integers(0, 2, n)
        else:
            if key not in self.cache:
                start = time.perf_counter()
                if pool not in self.embeddings:
                    self.embeddings[pool] = embed(target)
                xy, error, iterations = self.embeddings[pool]
                reg = pulser.Register.from_coordinates(xy, prefix='q', center=False)
                seq = pulser.Sequence(reg, pulser.AnalogDevice)
                seq.declare_channel('drive', 'rydberg_global')
                rise, sweep, fall = PULSES[self.pulse]
                omega, initial_delta = 6., -12.
                seq.add(pulser.Pulse.ConstantDetuning(pulser.RampWaveform(rise, 0, omega), initial_delta, 0), 'drive')
                seq.add(pulser.Pulse.ConstantAmplitude(omega, pulser.RampWaveform(sweep, initial_delta, final_delta), 0), 'drive')
                seq.add(pulser.Pulse.ConstantDetuning(pulser.RampWaveform(fall, omega, 0), final_delta, 0), 'drive')
                assert seq.get_duration() <= 6000
                np.random.seed(self.seed + self.backend_calls)
                config = QutipConfig(observables=[BitStrings(num_shots=BANK_SHOTS, evaluation_times=[1.0])])
                counts = dict(QutipBackendV2(seq, config=config).run().final_bitstrings)
                self.backend_seconds += time.perf_counter() - start
                self.backend_calls += 1
                self.backend_shots += sum(counts.values())
                strings = list(counts)
                probabilities = np.array([counts[s] for s in strings], dtype=float)
                self.cache[key] = (strings, probabilities / probabilities.sum())
                self.banks.append(dict(pool=list(map(int, pool)), final_detuning=final_delta, target_J=target.tolist(),
                                       coordinates_um=xy.tolist(), relative_coupling_error=error,
                                       optimizer_iterations=iterations, optimizer='SLSQP squared-coupling loss, maxiter=120',
                                       min_separation_um=float(min(pdist(xy))) if n > 1 else None,
                                       max_radius_um=float(max(np.linalg.norm(xy, axis=1))),
                                       duration_ns=seq.get_duration(), counts=counts,
                                       sequence=seq.to_abstract_repr()))
                print(f'  {self.instance["id"]} {self.pulse}: bank {self.backend_calls}, {n} atoms, error={error:.2f}', flush=True)
            strings, probabilities = self.cache[key]
            bits = np.array(list(rng.choice(strings, p=probabilities)), dtype=int)
        return [int(i) for i, bit in zip(pool, bits) if bit]
