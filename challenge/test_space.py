"""Check that the planetary example solves the real XYZ problem it displays."""
import json
from itertools import permutations, product
from pathlib import Path
import unittest
import numpy as np
from .core import generate, validate, pair_costs, references, groups_to_assignment
from .routing import encoding, energy, route_length, decode

ROOT=Path(__file__).resolve().parent


class SpaceChecks(unittest.TestCase):
    def test_depth_changes_distance_and_target_energy(self):
        instance=generate('S',11)
        instance.update(spatial_dimension=3,distance_normalizer=float(100*np.sqrt(3)),
                        customers=[[10,10,10],[10,10,20],[20,10,10],[20,20,20]],depot=[50,50,50],demands=[1]*4)
        validate(instance,[0,0,1,1])
        self.assertAlmostEqual(pair_costs(instance)[0,1],10/(100*np.sqrt(3)))
        reference,costs,orders=references(instance)
        for mask,cost in costs.items():
            group=[i for i in range(4) if mask>>i&1]
            self.assertAlmostEqual(cost,min(route_length(instance,r) for r in permutations(group)))
        spec=encoding(instance,[0,1,2,3],'edge')
        # Cycle depot -> 0 -> 1 -> 2 -> 3 -> depot.
        edges={(0,1),(1,2),(2,3),(3,4),(0,4)}
        bits=[int(tuple(e) in edges) for e in spec['variables']]
        self.assertAlmostEqual(energy(bits,spec),route_length(instance,[0,1,2,3])/(100*np.sqrt(3)))

    def test_three_customer_edge_encoding(self):
        instance=generate('S',11)
        group=[0,1,2]
        spec=encoding(instance,group,'edge')
        legal=0
        for bits in product('01',repeat=6):
            decoded=decode(bits,spec)
            if decoded is not None:
                legal+=1
                self.assertEqual(set(decoded),set(group))
                self.assertAlmostEqual(energy(bits,spec),route_length(instance,decoded)/(100*np.sqrt(2)))
        self.assertEqual(legal,3)

    def test_saved_plan_traces_and_route_scan(self):
        data=json.loads((ROOT/'space_demo_results/dashboard.json').read_text())
        instance=data['instance']
        self.assertEqual(np.asarray(instance['customers']).shape,(10,3))
        validate(instance,groups_to_assignment(10,[r['route'] for r in data['routes']]))
        self.assertAlmostEqual(sum(route_length(instance,r['route']) for r in data['routes']),data['total_distance'])
        self.assertEqual(len(data['clustering']['attempts']),data['protocol']['clustering_attempts'])
        self.assertEqual(sum(a['feasible'] for a in data['clustering']['attempts']),data['clustering']['metrics']['feasible_attempts'])
        measured_plans=[a for a in data['clustering']['attempts'] if a['feasible']]
        self.assertAlmostEqual(data['clustering']['best']['model_cost'],min(p['model_cost'] for p in measured_plans))
        self.assertEqual([a['attempt'] for a in data['clustering']['attempts']],list(range(len(data['clustering']['attempts']))))
        self.assertEqual(len(data['protocol']['search_rounds']),4)
        self.assertEqual(sorted(r['atoms'] for r in data['routes']), [6, 6, 10])
        evidence=json.loads((ROOT.parent/'sites/atlas-route-lab/dist/data/space-evidence.json').read_text())
        self.assertEqual(len(evidence['routing_banks']), 3)
        for row, bank in zip(data['routes'], evidence['routing_banks']):
            self.assertEqual(bank['group'], row['group'])
            self.assertEqual(row['method'], 'Quantum edge / DMM')
            self.assertEqual(row['shots'], data['protocol']['routing_shots'])
            self.assertEqual(sum(bank['counts'].values()), row['shots'])
            self.assertEqual(row['valid_shots'], sum(c['count'] for c in row['candidates']))
            spec=encoding(instance,row['group'],'edge')
            measured=[]
            for bits, count in bank['counts'].items():
                route=decode(bits,spec)
                if route is not None:
                    measured.append((route_length(instance,route),route))
                    edges=[e for e,b in zip(spec['variables'],bits) if b=='1']
                    self.assertEqual(len(edges),len(row['group'])+1)
                    for vertex in range(len(row['group'])+1):
                        self.assertEqual(sum(vertex in edge for edge in edges),2)
            self.assertTrue(measured)
            self.assertAlmostEqual(min(x[0] for x in measured),row['length'])
            self.assertIn(row['route'],[route for _,route in measured])
            best=float('inf')
            for candidate in row['candidates']:
                self.assertEqual(set(candidate['route']),set(row['group']))
                self.assertAlmostEqual(route_length(instance,candidate['route']),candidate['length'])
                best=min(best,candidate['length'])
                self.assertAlmostEqual(best,candidate['best_so_far'])
            if row['atoms']:
                self.assertAlmostEqual(best,row['length'])
                self.assertEqual(len(row['occupations']),41)
                self.assertLessEqual(row['valid_shots'],row['shots'])
        reference,_,_=references(instance)
        self.assertAlmostEqual(reference['cvrp_optimum'],data['reference']['cvrp_optimum'])
        self.assertAlmostEqual(data['total_distance'],reference['cvrp_optimum'])
        self.assertLess(data['total_distance'],data['optimization']['baseline']['total_distance'])


if __name__=='__main__':unittest.main()
