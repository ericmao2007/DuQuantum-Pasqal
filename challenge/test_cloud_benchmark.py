"""Offline regression checks for semantic cloud-job identity; no network calls."""
import unittest
import pulser
from pulser.backend import BitStrings
from pulser_simulation import QutipConfig
from .cloud_benchmark import CloudRunner


class CloudIdentityChecks(unittest.TestCase):
    def test_observable_identity_does_not_duplicate_physical_job(self):
        sequence=pulser.Sequence(pulser.Register.from_coordinates([[0,0],[9,0]],prefix='q'),pulser.AnalogDevice)
        a=QutipConfig(observables=[BitStrings(num_shots=1000,evaluation_times=[1.])])
        b=QutipConfig(observables=[BitStrings(num_shots=1000,evaluation_times=[1.])])
        self.assertNotEqual(a.to_abstract_repr(),b.to_abstract_repr())
        self.assertEqual(CloudRunner.key(sequence,a),CloudRunner.key(sequence,b))

    def test_changed_shot_budget_is_a_different_job(self):
        sequence=pulser.Sequence(pulser.Register.from_coordinates([[0,0],[9,0]],prefix='q'),pulser.AnalogDevice)
        a=QutipConfig(observables=[BitStrings(num_shots=1000,evaluation_times=[1.])])
        b=QutipConfig(observables=[BitStrings(num_shots=2000,evaluation_times=[1.])])
        self.assertNotEqual(CloudRunner.key(sequence,a),CloudRunner.key(sequence,b))

    def test_sdk_base_exception_has_safe_limit_diagnostics(self):
        import requests
        from pasqal_cloud.errors import BatchCreationError
        from .cloud_benchmark import safe_error
        response=requests.Response();response.status_code=422
        response._content=b'{"code":"CB1110","data":{"description":"Invalid sequence: number of atoms (16) exceeds the maximum number of atoms supported by this device (12)"}}'
        cause=requests.HTTPError(response=response)
        error=BatchCreationError(cause);error.__cause__=cause
        self.assertFalse(isinstance(error,Exception))
        result=safe_error(error)
        self.assertEqual(result['http_status'],422)
        self.assertEqual(result['service_code'],'CB1110')
        self.assertEqual(result['maximum_supported_atoms'],12)
        self.assertNotIn('response',result)

    def test_saved_pilot_measurements_and_routes(self):
        import json
        from pathlib import Path
        from .core import validate,groups_to_assignment
        from .routing import encoding,decode,route_length
        root=Path(__file__).parent/'cloud_results'/'m_benchmark'
        summary=json.loads((root/'summary.json').read_text())
        instance=json.loads((root/'instance.json').read_text())
        validate(instance,groups_to_assignment(10,summary['selected_groups']))
        jobs=[json.loads(p.read_text()) for p in (root/'jobs').glob('*.json')]
        done=[j for j in jobs if j['status']=='completed']
        self.assertEqual(len(done),26)
        self.assertEqual(sum(sum(j['counts'].values()) for j in done),28000)
        for job in done:
            self.assertTrue(job['batch_id'])
            self.assertEqual(sum(job['counts'].values()),job['shots'])
            self.assertTrue(all(len(b)==job['atoms'] for b in job['counts']))
        for row in summary['routing']:
            if row['status']!='completed':continue
            job=next(j for j in done if j['batch_id']==row['batch_id'])
            spec=encoding(instance,row['group'],row['kind'])
            legal=[]
            for bits,count in job['counts'].items():
                route=decode(bits,spec)
                if route is not None:legal.append((route_length(instance,route),count))
            self.assertEqual(sum(c for _,c in legal),row['valid_shots'])
            self.assertAlmostEqual(min(length for length,_ in legal),row['best']['length'])
        self.assertFalse(summary['methods']['position_dmm']['pipeline_feasible'])
        self.assertIsNone(summary['methods']['position_dmm']['gap_percent'])
