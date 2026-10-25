"""Real measured clustering and TSP on a fictional, fixed 3D planetary network.

python -m challenge.space_demo
Space units (su) are fictional Euclidean distance units, not AU or light-years.
The 3D application geometry is separate from the physical 2D atom register.
"""
import argparse
import time
from pathlib import Path
import json
import numpy as np
from .core import validate, references, pair_costs, clustering_cost
from .run import evaluate
from .routing import simulate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'challenge'/'space_demo_results'
WEB=ROOT/'sites'/'atlas-route-lab'/'dist'/'data'
PLANETS=[('Aster',[15,30,20]),('Lyra',[22,50,13]),('Nysa',[31,20,34]),('Vela',[20,60,41]),
         ('Orin',[65,15,25]),('Eos',[80,34,40]),('Tala',[71,52,17]),
         ('Nyx',[62,72,75]),('Mira',[81,80,65]),('Cael',[44,82,85])]


def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')


def cluster_search(instance, reference, costs, orders, rounds, attempts):
    """Diversify windows; select by F only, never by reference tours or groups."""
    runs=[];plans=[];banks=[];settings=[]
    for index in range(rounds):
        options={'order_seed':instance['seed']+900+index}
        seed=12026+1000*index
        row,detail=evaluate(instance,reference,costs,orders,'slow',seed,attempts,
                            record_trace=True,sampler_options=options)
        save(OUT/f'search_round_{index}.json',detail)
        offset=len(plans)
        for plan in detail['attempts']:
            plans.append(dict(plan,attempt=plan['attempt']+offset,search_round=index))
        settings.append(dict(round=index,seed=seed,sampler_options=options,
                             attempt_start=offset,attempts=attempts,backend_calls=row['backend_calls']))
        banks.extend(detail['banks']);runs.append(row)
    feasible=[p for p in plans if p['feasible']]
    if not feasible:raise RuntimeError('No feasible measured clustering; no fallback')
    best=min(feasible,key=lambda p:p['model_cost'])
    best_route=min(feasible,key=lambda p:p['routed_cost'])  # Evaluation only.
    metrics=dict(runs[0])
    metrics.update(method='slow_diverse_windows',seed=None,attempts=len(plans),
        feasible_attempts=len(feasible),feasibility_rate=len(feasible)/len(plans),
        model_gap_percent=100*(best['model_cost']/reference['model_optimum']-1),
        best_model_cost=best['model_cost'],best_cvrp_routed_cost=best_route['routed_cost'],
        cvrp_gap_percent=100*(best_route['routed_cost']/reference['cvrp_optimum']-1),
        model_selected_cvrp_gap_percent=100*(best['routed_cost']/reference['cvrp_optimum']-1),
        best_shot_exact_routed_cost=best['routed_cost'],
        probability_model_reference=sum(p['model_cost']<=reference['model_optimum']*(1+1e-8) for p in feasible)/len(plans),
        probability_cvrp_reference=sum(p['routed_cost']<=reference['cvrp_optimum']*(1+1e-8) for p in feasible)/len(plans),
        raw_stage_feasibility_rate=sum(s['accepted'] for p in plans for s in p['stages'])/sum(len(p['stages']) for p in plans),
        embedding_error_mean=float(np.mean([b['relative_coupling_error'] for b in banks])),
        embedding_error_max=max(b['relative_coupling_error'] for b in banks),
        search_rounds=rounds,
        **{key:sum(r[key] for r in runs) for key in ['elapsed_seconds','backend_calls','backend_shots','backend_and_embedding_seconds']})
    return dict(metrics=metrics,best_plan=best,best_cvrp_plan=best_route,attempts=plans,banks=banks,
                search_rounds=settings,selection='Minimum original clustering F across measured feasible trajectories; references do not select the plan')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--search-rounds',type=int,default=4)
    parser.add_argument('--attempts-per-round',type=int,default=128)
    parser.add_argument('--routing-shots',type=int,default=16000)
    args=parser.parse_args()
    if min(args.search_rounds,args.attempts_per_round,args.routing_shots)<1:parser.error('Budgets must be positive')
    started=time.perf_counter()
    OUT.mkdir(exist_ok=True);WEB.mkdir(parents=True,exist_ok=True)
    baseline_path=OUT/'optimization_baseline.json'
    if not baseline_path.exists() and (OUT/'dashboard.json').exists():
        old=json.loads((OUT/'dashboard.json').read_text())
        save(baseline_path,dict(total_distance=old['total_distance'],gap_percent=old['gap_percent'],
            groups=[r['group'] for r in old['routes']],routing_shots=old['protocol']['routing_shots'],
            clustering_attempts=old['protocol']['clustering_attempts'],model_gap_percent=old['clustering']['metrics']['model_gap_percent']))
    instance=dict(id='SPACE_10_2026',tier='M',seed=2026,customers=[p for _,p in PLANETS],
                  depot=[50,50,50],demands=[5]*10,vehicles=3,capacity=20,certificate=[i%3 for i in range(10)],
                  spatial_dimension=3,distance_normalizer=float(100*np.sqrt(3)),
                  generator='Fictional fixed 3D planet positions; deterministic coordinates; no orbital or gravitational model')
    validate(instance,instance['certificate']);save(OUT/'instance.json',instance)
    reference,costs,orders=references(instance)
    reference['cvrp_optimal_routes']=[list(orders[sum(1<<i for i in g)]) for g in reference['cvrp_optimal_groups']]
    save(OUT/'reference.json',reference)
    detail=cluster_search(instance,reference,costs,orders,args.search_rounds,args.attempts_per_round)
    save(OUT/'clustering.json',detail)
    best=detail['best_plan']
    if best is None:raise RuntimeError('No feasible quantum clustering; no certificate fallback')
    routes=[]
    for v,group in enumerate(best['groups']):
        mask=sum(1<<i for i in group)
        if not 2 <= len(group) <= 4:
            raise RuntimeError('This all-quantum-routing demo requires 2–4 planets per ship; no classical fallback')
        bank=simulate(instance,group,'edge','dmm',23026+v,shots=args.routing_shots,record_occupations=True)
        save(OUT/f'route_{v}.json',bank)
        if bank['best'] is None:raise RuntimeError(f'Quantum routing failed for ship {v+1}; no hidden repair')
        incumbent=float('inf');trace=[]
        for candidate in bank['valid_routes']:
            improved=candidate['length']<incumbent
            incumbent=min(incumbent,candidate['length'])
            trace.append(dict(route=candidate['route'],length=candidate['length'],count=candidate['count'],
                              bits=candidate['bits'],best_so_far=incumbent,improved=improved))
        routes.append(dict(ship=v,group=group,route=bank['best']['route'],length=bank['best']['length'],
                           exact_length=costs[mask],exact_route=list(orders[mask]),method='Quantum edge / DMM',
                           shots=bank['shots'],valid_shots=bank['feasible_shots'],atoms=bank['atoms'],
                           candidates=trace,occupations=bank['occupation_trace'],coordinates_um=bank['coordinates_um'],
                           variables=bank['variables'],embedding_error=bank['embedding_error']))
    # Keep ship colors consistent with the chronological best clustering decisions.
    chronological=[s['selected'] for s in best['stages'] if s['accepted']]
    used=set(i for g in chronological for i in g)
    chronological.append([i for i in range(10) if i not in used])
    routes.sort(key=lambda r:next(i for i,g in enumerate(chronological) if set(g)==set(r['group'])))
    for ship,row in enumerate(routes):
        row['original_register_index']=row['ship']
        row['ship']=ship
    incumbent=None;events=[]
    for attempt in detail['attempts']:
        for stage in attempt['stages']:
            events.append(dict(type='proposal',attempt=attempt['attempt'],**stage))
        improved=False
        if attempt['feasible'] and (incumbent is None or attempt['model_cost']<incumbent):
            incumbent=attempt['model_cost'];improved=True
        events.append(dict(type='complete',attempt=attempt['attempt'],feasible=attempt['feasible'],
                           groups=attempt.get('groups'),score=attempt.get('model_cost'),best_score=incumbent,improved=improved))
    total=sum(r['length'] for r in routes)
    payload=dict(run_id=instance['id'],fictional=True,unit='su',unit_description='One fictional Euclidean space-distance unit; not AU or light-years.',
                 instance=instance,planets=[dict(id=i,name=name,position=pos,demand=5) for i,(name,pos) in enumerate(PLANETS)],
                 station=dict(name='Origin Station',position=instance['depot']),reference=reference,
                 clustering=dict(attempts=detail['attempts'],events=events,best=best,metrics=detail['metrics']),
                 routes=routes,total_distance=total,exact_same_groups_distance=best['routed_cost'],
                 gap_percent=100*(total/reference['cvrp_optimum']-1),
                 protocol=dict(backend='QutipBackendV2 on CPU',clustering_attempts=args.search_rounds*args.attempts_per_round,routing_shots=args.routing_shots,
                               search_rounds=detail['search_rounds'],selection='Minimum F over measured feasible assignments',
                               dmm='Emulator-only routing control',noise=False,modulation=False,
                               routing_policy='Every ship uses measured quantum edge/DMM routing; no classical tour fallback',
                               classical_processing='Geometry fitting, capacity checks, decoding and best measured-tour selection',
                               candidate_order='Actual valid-tour patterns scanned by the decoder; not chronological hardware shots',
                               geometry='True fixed 3D Euclidean distances; the atom register stays 2D'))
    payload['optimization']=dict(baseline=json.loads(baseline_path.read_text()) if baseline_path.exists() else None,
        wall_seconds=time.perf_counter()-started,
        strategy='Four seeded window orders, more trajectories, more routing shots; no reference solution injected',
        caveat='Optimized on this demo instance with a larger compute budget; no generalization or speedup claim')
    save(OUT/'dashboard.json',payload);save(WEB/'space.json',payload)
    save(WEB/'space-evidence.json',dict(instance=instance,reference=reference,clustering=detail,routes=routes,
         routing_banks=[json.loads((OUT/f'route_{r["original_register_index"]}.json').read_text()) for r in routes]))
    print('Feasible:',detail['metrics']['feasibility_rate'],'score gap:',detail['metrics']['model_gap_percent'],flush=True)
    print('Routes:',[(r['ship'],r['method'],len(r['candidates'])) for r in routes],flush=True)
    print('Total:',total,'reference:',reference['cvrp_optimum'],'gap:',payload['gap_percent'],flush=True)


if __name__=='__main__':main()
