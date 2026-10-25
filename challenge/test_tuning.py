"""Checks for tuning isolation, geometric validity, and saved outcomes."""
import json
import unittest
from pathlib import Path
import numpy as np
from scipy.spatial.distance import pdist
from .core import generate, pair_costs, validate, groups_to_assignment
from .quantum import Sampler, embed

OUT = Path(__file__).parent / 'tuning_results'


class TuningChecks(unittest.TestCase):
    def test_multistart_preserves_or_improves_fit(self):
        pair = pair_costs(generate('M', 11))[:8, :8]
        target = 4 * (.3 + pair)
        np.fill_diagonal(target, 0)
        _, baseline, _ = embed(target)
        xy, tuned, _ = embed(target, starts=3)
        self.assertLessEqual(tuned, baseline + 1e-10)
        self.assertGreaterEqual(min(pdist(xy)), 5)
        self.assertLessEqual(max(np.linalg.norm(xy, axis=1)), 38)

    def test_rejects_unknown_or_negative_options(self):
        instance = generate('M', 11)
        for options in [{'typo': 4}, {'scale': -1}, {'reward_factor': 0}]:
            with self.assertRaises(ValueError):
                Sampler(instance, pair_costs(instance), 'slow', 1, options=options)

    def test_saved_split_and_results(self):
        protocol = json.loads((OUT/'protocol.json').read_text())
        selected = json.loads((OUT/'selected.json').read_text())
        self.assertFalse(set(protocol['training']) & set(protocol['heldout']))
        scores = selected['training_scores']
        self.assertEqual(tuple(scores[selected['candidate']]), max(map(tuple, scores.values())))
        for instance_id in protocol['heldout']:
            tier = instance_id.split('_')[0]
            from .core import generate_heterogeneous
            instance = (generate_heterogeneous if 'heterogeneous' in instance_id else generate)(tier, 101)
            for label in ['baseline', 'selected']:
                detail = json.loads((OUT/f'validation_{label}_{instance_id}.json').read_text())
                feasible = [p for p in detail['attempts'] if p['feasible']]
                self.assertEqual(len(feasible), detail['metrics']['feasible_attempts'])
                self.assertEqual(len(detail['attempts']), 32)
                for plan in feasible:
                    validate(instance, groups_to_assignment(len(instance['customers']), plan['groups']))
                for bank in detail['banks']:
                    self.assertEqual(sum(bank['counts'].values()), 1000)
                    self.assertLessEqual(bank['duration_ns'], 6000)
                    if len(bank['pool']) > 1:
                        self.assertGreaterEqual(min(pdist(bank['coordinates_um'])), 5)
