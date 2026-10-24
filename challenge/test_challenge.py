"""Independent checks for certificates, penalties, exact references, and saved runs."""
import json
import unittest
from itertools import product
from pathlib import Path
import numpy as np
from scipy.spatial.distance import pdist
from .core import generate, validate, groups_to_assignment, pair_costs, clustering_cost, references

ROOT = Path(__file__).resolve().parent


class ChallengeChecks(unittest.TestCase):
    def test_generated_certificates_and_reproducibility(self):
        for tier in ['S', 'M', 'L']:
            for seed in [11, 29, 101]:
                instance = generate(tier, seed)
                self.assertEqual(instance, generate(tier, seed))
                validate(instance, instance['certificate'])

    def test_validator_rejects_missing_duplicate_and_overload(self):
        instance = generate('S', 11)
        for bad in [[0, 0, 0, 0], [0, 1, 0], [0, -1, 0, 1]]:
            with self.assertRaises(ValueError):
                validate(instance, bad)
        with self.assertRaises(ValueError):
            groups_to_assignment(4, [[0, 1], [1, 2, 3]])

    def test_integer_capacity_penalty_has_zero_iff_capacity_holds(self):
        # Independently enumerate all subset loads and binary slack values.
        instance = generate('S', 11)
        q = instance['capacity']
        b = q.bit_length()
        for bits in product([0, 1], repeat=4):
            load = sum(d * bit for d, bit in zip(instance['demands'], bits))
            best = min((load + slack - q)**2 for slack in range(1 << b))
            self.assertEqual(best == 0, load <= q)

    def test_exact_references_match_bruteforce_and_cplex(self):
        reference, _, _ = references(generate('S', 11))
        self.assertIn('cplex_check', reference)
        for key in ['model', 'cvrp']:
            self.assertAlmostEqual(reference['cplex_check'][key]['value'], reference[f'{key}_optimum'])

    def test_saved_results_and_hardware_evidence(self):
        paths = list((ROOT/'results').glob('*_fast.json')) + list((ROOT/'results').glob('*_slow.json'))
        self.assertEqual(len(paths), 12)
        for path in paths:
            detail = json.loads(path.read_text())
            metrics = detail['metrics']
            instance = json.loads((ROOT/'instances'/f'{metrics["instance"]}.json').read_text())
            pair = pair_costs(instance)
            attempts = detail['attempts']
            feasible = [p for p in attempts if p['feasible']]
            self.assertAlmostEqual(len(feasible)/len(attempts), metrics['feasibility_rate'])
            for plan in feasible:
                validate(instance, groups_to_assignment(len(pair), plan['groups']))
                self.assertAlmostEqual(clustering_cost(plan['groups'], pair), plan['model_cost'])
            for bank in detail['banks']:
                xy = np.array(bank['coordinates_um'])
                self.assertLessEqual(len(xy), 8)
                self.assertLessEqual(np.max(np.linalg.norm(xy, axis=1)), 38)
                if len(xy) > 1:
                    self.assertGreaterEqual(min(pdist(xy)), 5)
                    target = np.array(bank['target_J'])[np.triu_indices(len(xy), 1)]
                    actual = 865723.02/pdist(xy)**6
                    self.assertAlmostEqual(np.linalg.norm(actual-target)/np.linalg.norm(target), bank['relative_coupling_error'], places=6)
                self.assertLessEqual(bank['duration_ns'], 6000)
                self.assertLessEqual(abs(bank['final_detuning']), 125.663707)
                self.assertEqual(sum(bank['counts'].values()), 1000)
                self.assertTrue(all(len(s) == len(xy) for s in bank['counts']))


if __name__ == '__main__':
    unittest.main()
