"""Run the real US-city experiment and export the interactive Site's evidence.

Run: python -m challenge.us_demo
Geographic coordinates are illustrative city centers, not street addresses.
Distances are equirectangular projected straight-line distances, not road miles.
"""
from pathlib import Path
import json
import numpy as np
from .core import validate, references
from .run import evaluate
from .routing import simulate, ROUTING_LIMIT

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'challenge'/'us_demo_results'
WEB=ROOT/'sites'/'atlas-route-lab'/'dist'/'data'
CITIES=[('Seattle','WA',47.61,-122.33),('Portland','OR',45.52,-122.68),
        ('San Francisco','CA',37.77,-122.42),('Los Angeles','CA',34.05,-118.24),
        ('Las Vegas','NV',36.17,-115.14),('Phoenix','AZ',33.45,-112.07),
        ('Salt Lake City','UT',40.76,-111.89),('Denver','CO',39.74,-104.99),
        ('Dallas','TX',32.78,-96.80),('Austin','TX',30.27,-97.74),
        ('Minneapolis','MN',44.98,-93.27),('Chicago','IL',41.88,-87.63),
        ('Atlanta','GA',33.75,-84.39),('Charlotte','NC',35.23,-80.84),
        ('New York','NY',40.71,-74.01)]
DEPOT=dict(name='Kansas City',state='MO',lat=39.10,lon=-94.58)


def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')


def main():
    OUT.mkdir(exist_ok=True);WEB.mkdir(parents=True,exist_ok=True)
    points=[DEPOT]+[dict(name=name,state=state,lat=lat,lon=lon) for name,state,lat,lon in CITIES]
    # One shared scale preserves Euclidean distances after normalization.
    projected=np.array([[p['lon']*111.195*np.cos(np.deg2rad(38)),p['lat']*111.195] for p in points])
    low=projected.min(axis=0);span=float(np.ptp(projected,axis=0).max());km_per_unit=span/96
    xy=(projected-low)/km_per_unit+2
    instance=dict(id='US_15_2026',tier='L',seed=2026,customers=xy[1:].tolist(),depot=xy[0].tolist(),
                  demands=[6]*15,vehicles=4,capacity=30,certificate=[i%4 for i in range(15)],
                  generator='15 illustrative US city centers; common-scale equirectangular projection at 38 degrees latitude')
    validate(instance,instance['certificate']);save(OUT/'instance.json',instance)
    ref,costs,orders=references(instance)
    ref['cvrp_optimal_routes']=[list(orders[sum(1<<i for i in group)]) for group in ref['cvrp_optimal_groups']]
    save(OUT/'reference.json',ref)
    print('US reference model:',ref['model_optimum'],'CVRP projected km:',ref['cvrp_optimum']*km_per_unit,flush=True)
    methods={}
    for method in ['slow','random']:
        _,detail=evaluate(instance,ref,costs,orders,method,12026,64,record_trace=True)
        save(OUT/f'{method}.json',detail);methods[method]=detail
        print(method,detail['metrics']['feasibility_rate'],detail['metrics']['model_gap_percent'],flush=True)
    chosen=methods['slow']['best_plan']
    if chosen is None:raise RuntimeError('No feasible quantum clustering; keep failed evidence')
    routing=[];total=0
    for index,group in enumerate(chosen['groups']):
        mask=sum(1<<i for i in group)
        if 3<len(group)<=ROUTING_LIMIT:
            bank=simulate(instance,group,'edge','dmm',22026+index,shots=2000,record_occupations=True)
            save(OUT/f'route_{index}.json',bank)
            if bank['best'] is None:raise RuntimeError(f'No legal quantum route for cluster {index}; do not silently repair')
            row=dict(vehicle=index,group=group,method='Quantum edge / DMM',route=bank['best']['route'],
                     length=bank['best']['length'],exact_length=costs[mask],atoms=bank['atoms'],
                     feasible_shots=bank['feasible_shots'],shots=bank['shots'],counts=bank['counts'],
                     best_bits=bank['best']['bits'],variables=bank['variables'],coordinates_um=bank['coordinates_um'],
                     occupation_trace=bank['occupation_trace'],valid_routes=bank['valid_routes'],
                     embedding_error=bank['embedding_error'],linear_error=bank['linear_error'],
                     target_h=bank['target_h'],target_J=bank['target_J'],duration_ns=bank['duration_ns'])
        else:
            row=dict(vehicle=index,group=group,method='Classical trivial' if len(group)<=3 else 'Classical size fallback',
                     route=list(orders[mask]),length=costs[mask],exact_length=costs[mask],atoms=0,
                     shots=0,feasible_shots=0,occupation_trace=[],valid_routes=[])
        routing.append(row);total+=row['length']
        print('Vehicle',index,row['method'],row['route'],flush=True)
    compact={}
    for method,detail in methods.items():
        compact[method]=dict(metrics=detail['metrics'],attempts=detail['attempts'],best_plan=detail['best_plan'])
        incumbent=None
        for attempt in compact[method]['attempts']:
            if attempt['feasible'] and (incumbent is None or attempt['model_cost']<incumbent):incumbent=attempt['model_cost']
            attempt['incumbent_model_cost']=incumbent
    data=dict(title='Atlas Route Lab',run_id=instance['id'],seed=2026,instance=instance,cities=points[1:],depot=DEPOT,
              km_per_unit=km_per_unit,distance_note='Projected straight-line km; not road distance. Illustrative city centers.',
              reference=ref,methods=compact,routing=routing,end_to_end_cost=total,
              end_to_end_gap_percent=100*(total/ref['cvrp_optimum']-1),
              exact_selected_cluster_cost=chosen['routed_cost'],
              protocol=dict(clustering_attempts=64,bank_shots=1000,routing_shots=2000,backend='QutipBackendV2',
                            quantum_routing_control='emulator-only DMM',noise=False,modulation=False,
                            occupations='Actual emulator expectation values at recorded evolution times',
                            route_histogram='Measured counts; histogram has no original shot chronology'))
    save(OUT/'dashboard.json',data);save(WEB/'run.json',data)
    save(WEB/'evidence.json',dict(instance=instance,reference=ref,clustering=methods,routing=routing))
    print('Saved dashboard:',WEB/'run.json',flush=True)


if __name__=='__main__':main()
