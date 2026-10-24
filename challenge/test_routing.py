"""Exhaustive small-encoding checks and independent end-to-end evidence audits."""
from itertools import permutations
import csv
import json
from pathlib import Path
import unittest
import numpy as np
from .core import generate, generate_heterogeneous, validate, references, groups_to_assignment
from .routing import encoding, decode, route_length, energy

ROOT=Path(__file__).resolve().parent


class RoutingChecks(unittest.TestCase):
    def test_heterogeneous_instances_and_certificates(self):
        for tier in ['S','M','L']:
            for seed in [11,29]:
                instance=generate_heterogeneous(tier,seed)
                self.assertGreater(len(set(instance['demands'])),1)
                self.assertEqual(instance,generate_heterogeneous(tier,seed))
                validate(instance,instance['certificate'])

    def test_both_qubo_energies_and_exact_decoders(self):
        instance=generate('M',11);group=[0,1,2,3]
        exact=min(route_length(instance,r) for r in permutations(group))/np.sqrt(20000)
        for kind,expected_count in [('edge',12),('position',24)]:
            spec=encoding(instance,group,kind);m=len(spec['h'])
            bits=((np.arange(1<<m)[:,None]>>np.arange(m))&1).astype(float)
            energies=spec['constant']+bits@spec['h']+np.einsum('bi,ij,bj->b',bits,np.triu(spec['J'],1),bits)
            valid=0
            for i,x in enumerate(bits):
                route=decode(x,spec)
                if route is not None:
                    valid+=1
                    self.assertAlmostEqual(energies[i],route_length(instance,route)/np.sqrt(20000),places=8)
                else:
                    self.assertGreater(energies[i],exact+1)
            self.assertEqual(valid,expected_count)
            self.assertAlmostEqual(float(energies.min()),exact,places=8)
        with self.assertRaises(ValueError):
            encoding(instance,[0,1,2,3,4],'edge')

    def test_held_karp_against_permutation_oracle(self):
        instance=generate('S',11);instance['demands']=[1]*4
        _,costs,orders=references(instance)
        for mask,cost in costs.items():
            group=[i for i in range(4) if mask>>i&1]
            oracle=min(route_length(instance,r) for r in permutations(group))
            self.assertAlmostEqual(cost,oracle)
            self.assertAlmostEqual(route_length(instance,orders[mask]),oracle)

    def test_final_track_b_evidence(self):
        out=ROOT/'track_b_results'
        with (out/'results.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),60)
        for row in rows:
            detail=json.loads((out/f'{row["instance"]}_{row["method"]}.json').read_text())
            instance=json.loads((out/'instances'/f'{row["instance"]}.json').read_text())
            metrics=detail['metrics']
            if metrics['pipeline_feasible']:
                assignment=groups_to_assignment(len(instance['customers']),detail['routes'])
                validate(instance,assignment)
                length=sum(route_length(instance,r) for r in detail['routes'])
                self.assertAlmostEqual(length,metrics['end_to_end_cost'])
                self.assertAlmostEqual(metrics['decomposition_loss']+metrics['clustering_loss']+metrics['routing_loss'],
                                       metrics['end_to_end_cost']-json.loads((out/f'{row["instance"]}_reference.json').read_text())['cvrp_optimum'])
            else:
                self.assertIsNone(metrics['end_to_end_gap_percent'])
            for cluster in detail['clusters']:
                if cluster['trivial']:
                    self.assertLessEqual(cluster['customers'],3)
                if cluster['classically_routed']:
                    self.assertGreater(cluster['customers'],4)
                if cluster['quantum_attempted']:
                    self.assertEqual(cluster['customers'],4)
        bank_paths=list((out/'banks').glob('*.json'))
        self.assertTrue(bank_paths)
        for p in bank_paths:
            bank=json.loads(p.read_text());xy=np.array(bank['coordinates_um'])
            from scipy.spatial.distance import pdist
            self.assertGreaterEqual(min(pdist(xy)),5)
            self.assertLessEqual(max(np.linalg.norm(xy,axis=1)),38)
            self.assertEqual(bank['duration_ns'],5200)
            self.assertLessEqual(bank['atoms'],80)
            self.assertEqual(sum(bank['counts'].values()),bank['shots'])
            target=np.array(bank['target_J'])[np.triu_indices(len(xy),1)]
            actual=865723.02/pdist(xy)**6
            self.assertAlmostEqual(np.linalg.norm(actual-target)/np.linalg.norm(target),bank['embedding_error'],places=6)
            import pulser
            from pulser.sampler import sample
            sequence=pulser.Sequence.from_abstract_repr(bank['sequence'])
            samples=sample(sequence).to_nested_dict(all_local=True)['Local']['ground-rydberg']
            h=np.array(bank['target_h'])
            wanted=h if bank['dmm'] else np.full(len(h),h.mean())
            realized=np.array([-float(samples[q]['det'][-1]) for q in sequence.register.qubit_ids])
            np.testing.assert_allclose(realized,wanted,atol=1e-6)
            self.assertTrue(all(abs(float(samples[q]['amp'][-1]))<1e-8 for q in samples))
            if bank['dmm']:
                self.assertEqual(bank['linear_error'],0)
            for valid in bank['valid_routes']:
                self.assertEqual(len(valid['route']),4)
                self.assertEqual(len(set(valid['route'])),4)


if __name__=='__main__':
    unittest.main()
