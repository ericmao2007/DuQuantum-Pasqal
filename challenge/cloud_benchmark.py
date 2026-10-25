"""Measure one real M_11 EMU_FREE pipeline, with resumable free-only jobs.

Uses stage-batched trajectories: a first shared bank, then independent second-stage
conditional banks submitted with bounded concurrency. No local simulation fallback.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import getpass
import hashlib
import json
import re
import threading
import time
from types import SimpleNamespace
from pathlib import Path
import numpy as np
import pulser
from pulser.backend import RemoteResults
from pasqal_cloud import PasqalCloudConnection, RemoteEmuFreeBackend
from .core import generate, references, pair_costs, clustering_cost, canonical, validate, groups_to_assignment
from .quantum import Sampler
from .routing import simulate, encoding, decode, route_length

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp'/'cloud'/'m_benchmark'


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,indent=2)+'\n');temporary.replace(path)


def stamp():return datetime.now(timezone.utc).isoformat()


def safe_error(error):
    result={'error_type':type(error).__name__}
    current=error
    while current is not None:
        status=getattr(current,'status_code',None)
        if status is None and getattr(current,'response',None) is not None:
            status=getattr(current.response,'status_code',None)
        if isinstance(status,int):result['http_status']=status;break
        current=getattr(current,'__cause__',None)
    # SDK exceptions can embed HTTP payloads: extract only whitelisted diagnostics.
    message=str(error)
    code=re.search(r'\bCB[0-9]{4}\b',message)
    if code:result['service_code']=code.group()
    limits=re.search(r'number of atoms \(([0-9]+)\).*?maximum number of atoms.*?\(([0-9]+)\)',message)
    if limits:result.update(requested_atoms=int(limits[1]),maximum_supported_atoms=int(limits[2]))
    return result


class MissingBank(Exception):
    def __init__(self,sequence,config):self.sequence,self.config=sequence,config


class CloudRunner:
    def __init__(self,connection,workers,timeout):
        self.connection,self.workers,self.timeout=connection,workers,timeout
        self.jobs={};self.lock=threading.Lock()

    @staticmethod
    def key(sequence,config):
        settings=json.loads(config.to_abstract_repr())
        # Observable UUIDs are random identity metadata, not simulation settings.
        for observable in settings.get('observables',[]):observable.pop('uuid',None)
        payload=sequence.to_abstract_repr()+'\n'+json.dumps(settings,sort_keys=True,separators=(',',':'))
        return hashlib.sha256(payload.encode()).hexdigest()

    def executor(self,sequence,config):
        key=self.key(sequence,config)
        if key not in self.jobs or self.jobs[key]['status']!='completed':raise MissingBank(sequence,config)
        return SimpleNamespace(final_bitstrings=self.jobs[key]['counts'])

    def execute(self,task):
        sequence,config,label,shots=task
        key=self.key(sequence,config);path=OUT/'jobs'/f'{key}.json'
        job=json.loads(path.read_text()) if path.exists() else dict(
            key=key,label=label,backend='EMU_FREE',atoms=len(sequence.register.qubits),
            duration_ns=sequence.get_duration(),shots=shots,sequence=sequence.to_abstract_repr(),
            config=config.to_abstract_repr(),status='prepared')
        if job['status'] in ['completed','submit_rejected','remote_failed']:
            with self.lock:self.jobs[key]=job
            print(f'CACHED {label}: {job.get("batch_id",job["status"])}',flush=True)
            return job
        began=time.monotonic()
        try:
            if job.get('batch_id'):
                remote=RemoteResults(batch_id=job['batch_id'],connection=self.connection)
                job['resumed_at']=stamp()
            else:
                if job['status'] not in ['prepared','submit_rejected']:
                    raise RuntimeError('Submission state is ambiguous; inspect portal rather than duplicate it')
                job.update(status='submitting',submitted_at=stamp());save(path,job)
                backend=RemoteEmuFreeBackend(sequence,self.connection,config=config,mimic_qpu=False)
                submitted=time.monotonic()
                try:remote=backend.run(job_params=[{'runs':shots}],wait=False)
                except BaseException as error:
                    if isinstance(error,(KeyboardInterrupt,SystemExit)):raise
                    diagnostic=safe_error(error)
                    state='submit_rejected' if diagnostic.get('http_status',0) in range(400,500) else 'submission_uncertain'
                    job.update(status=state,**diagnostic);raise
                job.update(status='submitted',batch_id=remote.batch_id,
                           submission_seconds=time.monotonic()-submitted)
                save(path,job)
                job['job_ids']=list(remote.job_ids)
            print(f'SUBMITTED {label}: {job["atoms"]} atoms; {job["batch_id"]}',flush=True)
            waiting=time.monotonic();last=None
            while time.monotonic()-waiting<self.timeout:
                available=remote.get_available_results()
                if available:
                    counts=dict(next(iter(available.values())).final_bitstrings)
                    if sum(counts.values())!=shots or any(len(b)!=job['atoms'] for b in counts):
                        raise ValueError('Malformed remote bitstring histogram')
                    job.update(status='completed',counts=counts,returned_at=stamp(),
                               wait_and_poll_seconds=time.monotonic()-waiting,
                               observed_call_seconds=time.monotonic()-began)
                    break
                status=str(remote.get_batch_status());job['last_observed_batch_status']=status
                if status!=last:print(f'STATUS {label}: {status}',flush=True);last=status
                save(path,job)
                if any(word in status.upper() for word in ['FAILED','ERROR','CANCELED','CANCELLED']):
                    job['status']='remote_failed';break
                time.sleep(3)
            else:job['status']='pending_after_timeout'
        except BaseException as error:
            if isinstance(error,(KeyboardInterrupt,SystemExit)):raise
            job.update(**safe_error(error))
            if job['status'] not in ['remote_failed','submit_rejected','submission_uncertain']:job['status']='interrupted'
        save(path,job)
        with self.lock:self.jobs[key]=job
        print(f'FINISHED {label}: {job["status"]}, {time.monotonic()-began:.1f}s',flush=True)
        return job

    def run_many(self,tasks):
        unique={self.key(seq,cfg):(seq,cfg,label,shots) for seq,cfg,label,shots in tasks}
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures=[pool.submit(self.execute,task) for task in unique.values()]
            return [future.result() for future in as_completed(futures)]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project-id');parser.add_argument('--username')
    parser.add_argument('--report-only',action='store_true',help='Audit saved cloud results without authentication or submission')
    parser.add_argument('--attempts',type=int,default=32)
    parser.add_argument('--workers',type=int,choices=[1,2,3,4],default=4)
    parser.add_argument('--timeout',type=int,default=600)
    args=parser.parse_args()
    if args.report_only:
        finalize_saved_pilot();return
    if not args.project_id or not args.username:parser.error('Supply project-id and login email')
    if args.attempts<1 or args.attempts>32:parser.error('Timing pilot is bounded to 1–32 trajectories')
    if '@' not in args.username:parser.error('Use the login email')
    settings=dict(instance='M_11',attempts=args.attempts,workers=args.workers,backend='EMU_FREE',resampling_seed=10011)
    settings_path=OUT/'run_settings.json'
    if settings_path.exists() and json.loads(settings_path.read_text())!=settings:
        parser.error('Existing checkpoint uses different settings; archive it before a distinct experiment')
    save(settings_path,settings)
    instance=generate('M',11);ref,costs,orders=references(instance);save(OUT/'instance.json',instance)
    password=getpass.getpass('Pasqal password (hidden; never saved): ')
    try:connection=PasqalCloudConnection(username=args.username,password=password,project_id=args.project_id)
    finally:del password
    started=time.monotonic();runner=CloudRunner(connection,args.workers,args.timeout)
    rng=np.random.default_rng(10011)
    sampler=Sampler(instance,pair_costs(instance),'slow',10011,executor=runner.executor)
    all_customers=set(range(10));tasks=[]
    try:sampler.draw(all_customers,3,rng)
    except MissingBank as need:tasks.append((need.sequence,need.config,'clustering_first',1000))
    if any(j['status']!='completed' for j in runner.run_many(tasks)):
        raise RuntimeError('The first cloud clustering bank did not complete')
    stages=[]
    for attempt in range(args.attempts):
        selected=sampler.draw(all_customers,3,rng);remaining=all_customers-set(selected)
        accepted=sum(instance['demands'][i] for i in selected)<=20 and sum(instance['demands'][i] for i in remaining)<=40
        stages.append(dict(attempt=attempt,first=selected,remaining=sorted(remaining),first_accepted=accepted))
    tasks=[]
    for plan in stages:
        if not plan['first_accepted']:continue
        try:sampler.draw(set(plan['remaining']),2,np.random.default_rng(0))
        except MissingBank as need:
            tasks.append((need.sequence,need.config,'clustering_second_'+str(plan['attempt']),1000))
    print(f'STAGE 2: {len(tasks)} requests before deduplication',flush=True)
    runner.run_many(tasks)
    feasible=[];pair=pair_costs(instance)
    for plan in stages:
        plan['feasible']=False
        if not plan['first_accepted']:continue
        try:
            selected=sampler.draw(set(plan['remaining']),2,rng)
            plan['second']=selected
        except MissingBank:
            plan['failure']='remote conditional bank unavailable';continue
        remaining=set(plan['remaining'])-set(selected)
        if sum(instance['demands'][i] for i in selected)>20 or sum(instance['demands'][i] for i in remaining)>20:continue
        groups=canonical([plan['first'],selected,sorted(remaining)])
        validate(instance,groups_to_assignment(10,groups))
        plan.update(feasible=True,groups=groups,model_cost=clustering_cost(groups,pair))
        feasible.append(plan)
    cluster_seconds=time.monotonic()-started
    best=min(feasible,key=lambda p:p['model_cost']) if feasible else None
    save(OUT/'clustering.json',dict(attempts=stages,best=best,seconds=cluster_seconds,banks=sampler.banks,
        sampling_protocol='Stage-batched trajectories from finite shared cloud banks; no local quantum emulation'))
    tasks=[];route_requests=[]
    groups=best['groups'] if best else []
    for index,group in enumerate(groups):
        if len(group)<=3:continue  # The formal benchmark policy; exact trivial tour.
        for kind,mode in [('edge','global'),('edge','dmm'),('position','dmm')]:
            try:simulate(instance,group,kind,mode,20011+index,shots=2000,executor=runner.executor)
            except MissingBank as need:
                tasks.append((need.sequence,need.config,f'routing_{index}_{kind}_{mode}',2000))
                route_requests.append((index,group,kind,mode,runner.key(need.sequence,need.config)))
    runner.run_many(tasks)
    routes=[]
    for index,group,kind,mode,key in route_requests:
        job=runner.jobs[key];spec=encoding(instance,group,kind);valid=[]
        if job['status'] in ['completed','submit_rejected','remote_failed']:
            for bits,count in job['counts'].items():
                route=decode(bits,spec)
                if route is not None:valid.append(dict(bits=bits,count=count,route=route,length=route_length(instance,route)))
        best_route=min(valid,key=lambda x:x['length']) if valid else None
        routes.append(dict(cluster=index,group=list(group),kind=kind,mode=mode,atoms=job['atoms'],
            status=job['status'],batch_id=job.get('batch_id'),valid_shots=sum(v['count'] for v in valid),
            shots=2000,best=best_route,exact_tsp=costs[sum(1<<i for i in group)]))
    methods={}
    for kind,mode in [('edge','global'),('edge','dmm'),('position','dmm')]:
        total=0.;success=best is not None
        for index,group in enumerate(groups):
            if len(group)<=3:total+=costs[sum(1<<i for i in group)];continue
            row=next(r for r in routes if r['cluster']==index and r['kind']==kind and r['mode']==mode)
            if row['best'] is None:success=False
            else:total+=row['best']['length']
        methods[f'{kind}_{mode}']=dict(pipeline_feasible=success,cost=total if success else None,
            gap_percent=100*(total/ref['cvrp_optimum']-1) if success else None)
    jobs=list(runner.jobs.values());summary=dict(instance=instance['id'],backend='EMU_FREE',status='completed',
        attempts=args.attempts,feasible_attempts=len(feasible),workers=args.workers,resampling_seed=10011,
        clustering_seconds=cluster_seconds,total_seconds=time.monotonic()-started,
        jobs=len(jobs),completed_jobs=sum(j['status']=='completed' for j in jobs),
        returned_shots=sum(sum(j.get('counts',{}).values()) for j in jobs),
        model_gap_percent=None if best is None else 100*(best['model_cost']/ref['model_optimum']-1),
        methods=methods,routing=routes,reference=ref,
        timing_note='Includes preparation, submission, cloud waits, polling and decoding; starts after connection initialization. No pure backend-compute timing claimed.',
        policy='Formal benchmark trivial n<=3 tours evaluated classically; eligible n=4 routing is cloud-only. Failed cloud jobs never replaced by local results.',
        sampling_note='Stage batching changes RNG consumption from the original sequential evaluator; same instance and shot/trajectory budgets, not identical trajectories.',
        scope='One M_11 uniform-demand pilot; no paid backend and no QPU.')
    save(OUT/'summary.json',summary)
    finalize_saved_pilot()
    print(json.dumps({k:v for k,v in summary.items() if k not in ['routing','reference']},indent=2),flush=True)


def finalize_saved_pilot():
    """Audit a completed or partially supported pilot solely from raw cloud data."""
    instance=json.loads((OUT/'instance.json').read_text())
    clustering=json.loads((OUT/'clustering.json').read_text())
    ref,costs,orders=references(instance)
    jobs=[json.loads(p.read_text()) for p in (OUT/'jobs').glob('*.json')]
    groups=clustering['best']['groups'] if clustering['best'] else []
    routes=[]
    for job in jobs:
        if not job['label'].startswith('routing_'):continue
        _,index,kind,mode=job['label'].split('_');index=int(index);group=groups[index]
        spec=encoding(instance,group,kind);valid=[]
        for bits,count in job.get('counts',{}).items():
            route=decode(bits,spec)
            if route is not None:valid.append(dict(bits=bits,count=count,route=route,length=route_length(instance,route)))
        routes.append(dict(cluster=index,group=group,kind=kind,mode=mode,atoms=job['atoms'],
            status=job['status'],batch_id=job.get('batch_id'),shots=job['shots'],
            valid_shots=sum(c['count'] for c in valid),best=min(valid,key=lambda c:c['length']) if valid else None,
            exact_tsp=costs[sum(1<<i for i in group)],
            service_code=job.get('service_code'),maximum_supported_atoms=job.get('maximum_supported_atoms')))
    methods={}
    for kind,mode in [('edge','global'),('edge','dmm'),('position','dmm')]:
        total=0.;success=bool(groups)
        for index,group in enumerate(groups):
            if len(group)<=3:total+=costs[sum(1<<i for i in group)];continue
            matches=[r for r in routes if r['cluster']==index and r['kind']==kind and r['mode']==mode]
            if not matches or matches[0]['best'] is None:success=False
            else:total+=matches[0]['best']['length']
        methods[f'{kind}_{mode}']=dict(pipeline_feasible=success,cost=total if success else None,
            gap_percent=100*(total/ref['cvrp_optimum']-1) if success else None)
    completed=[j for j in jobs if j['status']=='completed']
    cluster_jobs=[j for j in completed if j['label'].startswith('clustering_')]
    edge_jobs=[j for j in completed if j['label'].startswith('routing_') and '_edge_' in j['label']]
    first=min(datetime.fromisoformat(j['submitted_at']) for j in cluster_jobs)
    cluster_end=max(datetime.fromisoformat(j['returned_at']) for j in cluster_jobs)
    edge_end=max([datetime.fromisoformat(j['returned_at']) for j in edge_jobs]+[cluster_end])
    durations=[j['observed_call_seconds'] for j in completed]
    profile=dict(instance=instance['id'],backend='EMU_FREE',status='audited_from_saved_cloud_results',
        attempts=len(clustering['attempts']),feasible_attempts=sum(p['feasible'] for p in clustering['attempts']),
        workers=json.loads((OUT/'run_settings.json').read_text()).get('workers') if (OUT/'run_settings.json').exists() else None,resampling_seed=10011,jobs=len(jobs),completed_jobs=len(completed),
        rejected_requests=sum(j['status']=='submit_rejected' for j in jobs),
        returned_shots=sum(sum(j['counts'].values()) for j in completed),
        observed_clustering_wall_seconds=clustering['seconds'],
        first_cloud_submit_to_last_clustering_result_seconds=(cluster_end-first).total_seconds(),
        first_cloud_submit_to_both_edge_results_seconds=(edge_end-first).total_seconds(),
        successful_job_mean_seconds=float(np.mean(durations)),successful_job_min_seconds=min(durations),
        successful_job_max_seconds=max(durations),
        model_gap_percent=100*(clustering['best']['model_cost']/ref['model_optimum']-1) if groups else None,
        selected_groups=groups,methods=methods,routing=routes,reference=ref,
        timing_note='Cloud intervals derive from actual submitted_at/returned_at timestamps. They include queue/API/polling, exclude initial password entry, tiny pre-submit preparation, post-result audit, and later failed-position SDK retry delay. No complete all-variant wall time was captured after the rejection.',
        diagnostic_note='One preceding 8-atom diagnostic job and a client observable-UUID cache correction are retained separately in diagnostics/; not included in the clean pilot job count or timing.',
        policy='Official benchmark trivial n<=3 tours use exact classical evaluation; n=4 routing is cloud-only. No failed job is repaired or replaced by local simulation.',
        sampling_note='Stage-batched 32 trajectories share finite cloud banks; RNG consumption differs from the sequential local evaluator. This is a timing/compatibility pilot, not a controlled accuracy comparison.',
        compatibility='; '.join(f'{r["atoms"]}-atom {r["kind"]}/{r["mode"]}: {r["status"]}'+(f' (reported maximum {r["maximum_supported_atoms"]})' if r['maximum_supported_atoms'] is not None else '') for r in routes),
        scope='One M_11 uniform-demand case; no paid backend or QPU.')
    save(OUT/'summary.json',profile)
    print(json.dumps({k:v for k,v in profile.items() if k not in ['reference','routing']},indent=2),flush=True)
    return profile


if __name__=='__main__':
    try:main()
    except BaseException as error:
        save(OUT/'failure.json',dict(status='stopped',**safe_error(error)))
        print(f'Stopped: {type(error).__name__}; credential details suppressed.',flush=True)
        raise SystemExit(1)
