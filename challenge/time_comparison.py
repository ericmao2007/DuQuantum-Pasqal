"""Measure classical exact CVRP against the current quantum-assisted emulator.

python -m challenge.time_comparison
Fresh caches per repeat; module imports and file export are outside timing.
Neither method reads reference solutions while choosing its routes.
"""
import argparse
from functools import lru_cache
from itertools import combinations, permutations
from pathlib import Path
import json
import platform
import statistics
import time
from importlib.metadata import version
import numpy as np
from .core import canonical, clustering_cost, groups_to_assignment, pair_costs, validate
from .quantum import Sampler
from .routing import simulate, route_length

ROOT=Path(__file__).resolve().parents[1]


def classical(instance):
    start=time.perf_counter();n=len(instance['customers']);q=instance['capacity'];k=instance['vehicles']
    points=np.array([instance['depot']]+instance['customers']);dist=np.linalg.norm(points[:,None]-points[None,:],axis=-1)
    costs={};orders={};dp={};previous={};by_anchor=[[] for _ in range(n)]
    for size in range(1,n+1):
        if size*min(instance['demands'])>q:break
        for group in combinations(range(n),size):
            if sum(instance['demands'][i] for i in group)>q:continue
            mask=sum(1<<i for i in group)
            for last in group:
                rest=mask^(1<<last)
                if not rest:dp[mask,last]=float(dist[0,last+1]);previous[mask,last]=None
                else:
                    value,prior=min((dp[rest,j]+dist[j+1,last+1],j) for j in group if j!=last)
                    dp[mask,last]=float(value);previous[mask,last]=prior
            value,last=min((dp[mask,j]+dist[j+1,0],j) for j in group)
            costs[mask]=float(value);route=[];m=mask
            while last is not None:
                route.append(last);prior=previous[m,last];m^=1<<last;last=prior
            orders[mask]=list(reversed(route));by_anchor[group[0]].append(mask)
    routes_done=time.perf_counter()
    @lru_cache(None)
    def partition(mask,left):
        if not mask:return 0.,()
        if left==0 or mask.bit_count()>left*(q//min(instance['demands'])):return float('inf'),()
        anchor=(mask&-mask).bit_length()-1;best=float('inf');chosen=()
        for sub in by_anchor[anchor]:
            if sub&mask!=sub:continue
            rest,parts=partition(mask^sub,left-1);value=costs[sub]+rest
            if value<best:best=value;chosen=(sub,)+parts
        return best,chosen
    cost,masks=partition((1<<n)-1,k);partition_done=time.perf_counter()
    routes=[orders[m] for m in masks]
    validate(instance,groups_to_assignment(n,routes))
    assert abs(sum(route_length(instance,r) for r in routes)-cost)<1e-7
    total=time.perf_counter()-start
    return dict(seconds=total,cost=cost,routes=routes,feasible=True,proven_optimum=True,
                stages=[dict(label='Exact subset tours',seconds=routes_done-start),
                        dict(label='Best vehicle partition',seconds=partition_done-routes_done),
                        dict(label='Validate',seconds=total-(partition_done-start))],subset_count=len(costs))


def quantum(instance,seed=12026,attempts=64):
    start=time.perf_counter();rng=np.random.default_rng(seed);n=len(instance['customers']);k=instance['vehicles'];q=instance['capacity']
    sampler=Sampler(instance,pair_costs(instance),'slow',seed);feasible=[]
    for attempt in range(attempts):
        remaining=set(range(n));groups=[];failed=False
        for left in range(k,1,-1):
            if not remaining:break
            selected=sampler.draw(remaining,left,rng)
            if sum(instance['demands'][i] for i in selected)>q or sum(instance['demands'][i] for i in remaining.difference(selected))>(left-1)*q:
                failed=True;break
            groups.append(selected);remaining.difference_update(selected)
        if failed or sum(instance['demands'][i] for i in remaining)>q:continue
        groups.append(sorted(remaining));groups=canonical(groups)
        validate(instance,groups_to_assignment(n,groups))
        feasible.append((clustering_cost(groups,pair_costs(instance)),groups))
    if not feasible:raise RuntimeError('No feasible measured clustering; no reference fallback')
    _,groups=min(feasible,key=lambda x:x[0]);routes=[];quantum_clusters=0;classical_clusters=0
    embedding=sampler.embedding_seconds;simulation=sampler.simulation_seconds;route_banks=[]
    for index,group in enumerate(groups):
        if len(group)==4:
            bank=simulate(instance,group,'edge','dmm',22026+index,shots=2000)
            if bank['best'] is None:raise RuntimeError('No feasible measured route; no classical repair')
            routes.append(bank['best']['route']);quantum_clusters+=1
            embedding+=bank['embedding_seconds'];simulation+=bank['simulation_seconds']
            route_banks.append(dict(group=list(group),counts=bank['counts'],best=bank['best']))
        else:
            # Local exact fallback is computed NOW, not read from an offline oracle.
            route=min(permutations(group),key=lambda r:route_length(instance,r)) if group else ()
            routes.append(list(route));classical_clusters+=1
    validate(instance,groups_to_assignment(n,routes));cost=sum(route_length(instance,r) for r in routes)
    total=time.perf_counter()-start
    return dict(seconds=total,cost=cost,routes=routes,feasible=True,proven_optimum=False,
                stages=[dict(label='Fit atom layouts',seconds=embedding),dict(label='Simulate + sample',seconds=simulation),
                        dict(label='Validate + merge + classical work',seconds=total-embedding-simulation)],
                feasible_attempts=len(feasible),attempts=attempts,quantum_routed_clusters=quantum_clusters,
                classical_routed_clusters=classical_clusters,backend_calls=sampler.backend_calls+quantum_clusters,
                measured_bank_shots=sampler.backend_shots+2000*quantum_clusters,route_banks=route_banks)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repeats',type=int,default=3);args=parser.parse_args()
    if args.repeats<1:parser.error('repeats must be positive')
    instance=json.loads((ROOT/'challenge/us_demo_results/instance.json').read_text())
    map_data=json.loads((ROOT/'sites/atlas-route-lab/dist/data/run.json').read_text())
    reference=json.loads((ROOT/'challenge/us_demo_results/reference.json').read_text())
    results={'classical':[],'quantum':[]}
    for repeat in range(args.repeats):
        for name,fn in [('classical',classical),('quantum',quantum)]:
            result=fn(instance);results[name].append(result)
            print(name,repeat+1,result['seconds'],flush=True)
    for result in results['classical']:assert abs(result['cost']-reference['cvrp_optimum'])<1e-7
    payload=dict(instance=instance['id'],customers=15,vehicles=4,repeats=args.repeats,
                 km_per_unit=map_data['km_per_unit'],reference_cost=reference['cvrp_optimum'],
                 timing='Sequential warmed-process wall time; imports, dataset loading, result export, and offline reference scoring excluded; fresh solver caches each repeat.',
                 machine=dict(system=platform.system(),architecture=platform.machine(),python=platform.python_version(),pulser=version('pulser'),qutip=version('qutip')),
                 quantum_backend='QutipBackendV2 on a classical CPU; no real QPU timings',results=results,summary={})
    for name,runs in results.items():
        median=statistics.median(r['seconds'] for r in runs);representative=min(runs,key=lambda r:abs(r['seconds']-median))
        payload['summary'][name]=dict(seconds=median,min_seconds=min(r['seconds'] for r in runs),max_seconds=max(r['seconds'] for r in runs),
            stages=representative['stages'],cost_km=representative['cost']*map_data['km_per_unit'],
            gap_percent=100*(representative['cost']/reference['cvrp_optimum']-1),
            routes=representative['routes'],proven_optimum=representative['proven_optimum'])
    payload['ratio']=payload['summary']['quantum']['seconds']/payload['summary']['classical']['seconds']
    for path in [ROOT/'challenge/us_demo_results/timing.json',ROOT/'sites/atlas-route-lab/dist/data/timing.json']:
        path.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload['summary'],indent=2),flush=True)


if __name__=='__main__':main()
