"""Real measured clustering and TSP on a fictional, fixed 3D planetary network.

python -m challenge.space_demo
Space units (su) are fictional Euclidean distance units, not AU or light-years.
The 3D application geometry is separate from the physical 2D atom register.
"""
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


def main():
    OUT.mkdir(exist_ok=True);WEB.mkdir(parents=True,exist_ok=True)
    instance=dict(id='SPACE_10_2026',tier='M',seed=2026,customers=[p for _,p in PLANETS],
                  depot=[50,50,50],demands=[5]*10,vehicles=3,capacity=20,certificate=[i%3 for i in range(10)],
                  spatial_dimension=3,distance_normalizer=float(100*np.sqrt(3)),
                  generator='Fictional fixed 3D planet positions; deterministic coordinates; no orbital or gravitational model')
    validate(instance,instance['certificate']);save(OUT/'instance.json',instance)
    reference,costs,orders=references(instance)
    reference['cvrp_optimal_routes']=[list(orders[sum(1<<i for i in g)]) for g in reference['cvrp_optimal_groups']]
    save(OUT/'reference.json',reference)
    _,detail=evaluate(instance,reference,costs,orders,'slow',12026,64,record_trace=True)
    save(OUT/'clustering.json',detail)
    best=detail['best_plan']
    if best is None:raise RuntimeError('No feasible quantum clustering; no certificate fallback')
    routes=[]
    for v,group in enumerate(best['groups']):
        mask=sum(1<<i for i in group)
        if len(group)==4:
            bank=simulate(instance,group,'edge','dmm',23026+v,shots=2000,record_occupations=True)
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
        else:
            routes.append(dict(ship=v,group=group,route=list(orders[mask]),length=costs[mask],exact_length=costs[mask],
                               exact_route=list(orders[mask]),method='Classical trivial',shots=0,valid_shots=0,
                               atoms=0,candidates=[],occupations=[]))
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
                 protocol=dict(backend='QutipBackendV2 on CPU',clustering_attempts=64,routing_shots=2000,
                               dmm='Emulator-only routing control',noise=False,modulation=False,
                               candidate_order='Actual valid-tour patterns scanned by the decoder; not chronological hardware shots',
                               geometry='True fixed 3D Euclidean distances; the atom register stays 2D'))
    save(OUT/'dashboard.json',payload);save(WEB/'space.json',payload)
    save(WEB/'space-evidence.json',dict(instance=instance,reference=reference,clustering=detail,routes=routes))
    print('Feasible:',detail['metrics']['feasibility_rate'],'score gap:',detail['metrics']['model_gap_percent'],flush=True)
    print('Routes:',[(r['ship'],r['method'],len(r['candidates'])) for r in routes],flush=True)
    print('Total:',total,'reference:',reference['cvrp_optimum'],'gap:',payload['gap_percent'],flush=True)


if __name__=='__main__':main()
