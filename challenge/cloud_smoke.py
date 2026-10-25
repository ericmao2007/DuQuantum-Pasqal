"""Run one saved global sequence on Pasqal EMU_FREE; never store credentials.

python -m challenge.cloud_smoke --project-id PROJECT --username LOGIN_EMAIL
Password input is hidden in the terminal. Local evidence goes to ignored tmp/cloud/.
"""
import argparse
import getpass
import hashlib
import json
import logging
import time
from pathlib import Path
import numpy as np
import pulser
from pulser.backend import BitStrings, RemoteResults
from pulser.backends import QutipBackendV2
from pulser_simulation import QutipConfig
from pasqal_cloud import PasqalCloudConnection, RemoteEmuFreeBackend

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'tmp'/'cloud'


def save(data):
    OUT.mkdir(parents=True, exist_ok=True)
    path=OUT/'smoke.json'
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,indent=2)+'\n')
    temporary.replace(path)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--username', required=True)
    parser.add_argument('--shots', type=int, default=1000)
    parser.add_argument('--resume', action='store_true', help='Poll the saved batch; never submit again')
    parser.add_argument('--prepare-only', action='store_true', help='Validate and simulate locally; no login or submission')
    args=parser.parse_args()
    if '@' not in args.username:parser.error('username must be the Pasqal login email')
    if not 1<=args.shots<=2000:parser.error('Use 1 to 2000 shots for this small smoke test')
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    detail=json.loads((ROOT/'challenge/track_b_results/S_11_clustering_slow.json').read_text())
    serialized=detail['banks'][0]['sequence']
    sequence=pulser.Sequence.from_abstract_repr(serialized)
    config=QutipConfig(observables=[BitStrings(num_shots=args.shots,evaluation_times=[1.])])
    evidence=dict(status='prepared',backend='EMU_FREE',source='S_11 first slow clustering bank',
                  atoms=len(sequence.register.qubits),duration_ns=sequence.get_duration(),shots=args.shots,
                  sequence_sha256=hashlib.sha256(serialized.encode()).hexdigest(),
                  mimic_qpu=False,noise=False,modulation=False)
    if args.resume:
        evidence=json.loads((OUT/'smoke.json').read_text())
        if not evidence.get('batch_id'):raise RuntimeError('No saved batch to resume')
    else:
        if (OUT/'smoke.json').exists():
            previous=json.loads((OUT/'smoke.json').read_text())
            if previous.get('batch_id'):
                raise RuntimeError('A batch already exists. Use --resume to avoid duplicate submission.')
        np.random.seed(711)
        started=time.monotonic()
        local=QutipBackendV2(sequence,config=config).run()
        evidence.update(local_counts=dict(local.final_bitstrings),local_seconds=time.monotonic()-started)
        save(evidence)
    print(f'Prepared {evidence["atoms"]} atoms, {evidence["duration_ns"]} ns, {evidence["shots"]} shots.',flush=True)
    if args.prepare_only:
        print('Local preparation passed. No cloud request was submitted.',flush=True)
        return
    evidence['status']='waiting_for_password';save(evidence)
    password=getpass.getpass('Pasqal Cloud password (hidden; never saved): ')
    evidence['status']='authenticating';save(evidence)
    try:
        connection=PasqalCloudConnection(username=args.username,password=password,project_id=args.project_id)
    finally:
        del password
    if args.resume:
        remote=RemoteResults(batch_id=evidence['batch_id'],connection=connection)
    else:
        evidence['status']='submitting';save(evidence)
        backend=RemoteEmuFreeBackend(sequence,connection,config=config,mimic_qpu=False)
        remote=backend.run(job_params=[{'runs':args.shots}],wait=False)
        evidence.update(batch_id=remote.batch_id,job_ids=list(remote.job_ids),status='submitted')
        save(evidence)
    print('Cloud batch:',remote.batch_id,flush=True)
    started=time.monotonic()
    while time.monotonic()-started<600:
        status=str(remote.get_batch_status())
        evidence['last_observed_batch_status']=status;evidence['status']='polling';save(evidence)
        print('Cloud status:',status,flush=True)
        available=remote.get_available_results()
        if available:
            result=next(iter(available.values()))
            counts=dict(result.final_bitstrings)
            total=sum(counts.values())
            expected=evidence['local_counts'];local_total=sum(expected.values())
            tv=.5*sum(abs(counts.get(b,0)/total-expected.get(b,0)/local_total) for b in set(counts)|set(expected))
            evidence.update(status='completed',cloud_counts=counts,cloud_shots_returned=total,
                observed_total_variation_distance=tv,cloud_poll_seconds=time.monotonic()-started,
                interpretation='Two finite sampled histograms; differences do not alone imply different physics.')
            save(evidence)
            print(json.dumps({k:v for k,v in evidence.items() if k not in ['local_counts','cloud_counts']},indent=2),flush=True)
            return
        if any(word in status.upper() for word in ['ERROR','CANCELED','CANCELLED','FAILED']):
            evidence['status']='cloud_failed';save(evidence)
            raise RuntimeError('Cloud backend reported a terminal failure')
        time.sleep(5)
    evidence['status']='pending_after_timeout';save(evidence)
    print('Batch remains pending. Resume later with --resume; no additional job is needed.',flush=True)


if __name__=='__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        # Avoid printing raw HTTP responses, tokens, passwords or authentication payloads.
        OUT.mkdir(parents=True,exist_ok=True)
        path=OUT/'smoke.json'
        state=json.loads(path.read_text()) if path.exists() else {}
        state.update(failure_phase=state.get('status'),status='stopped',error_type=type(error).__name__)
        http_status=getattr(error,'status_code',None)
        response=getattr(error,'response',None)
        if http_status is None and response is not None:http_status=getattr(response,'status_code',None)
        if isinstance(http_status,int):state['http_status']=http_status
        save(state)
        print(f'Stopped: {type(error).__name__}. No credential details were logged.',flush=True)
        raise SystemExit(1)
