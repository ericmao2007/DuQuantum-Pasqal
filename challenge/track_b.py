"""End-to-end Track B: python -m challenge.track_b.

Keeps Track A evidence intact and writes a separate full submission bundle.
"""
import argparse
import csv
import json
import time
from pathlib import Path
import numpy as np
from .core import generate, generate_heterogeneous, references
from .run import evaluate
from .routing import simulate, route_length, ROUTING_LIMIT, ROUTING_SHOTS

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'track_b_results'


def save(path,data):
    path.write_text(json.dumps(data,indent=2)+'\n')


def write_csv(path,rows):
    if not rows:
        return
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def route_pipeline(instance,reference,clustering,costs,orders,kind,mode,seed,out,shots):
    rng=np.random.default_rng(seed)
    best=clustering['best_plan']
    rows=[];banks=[];total=0.;exact_total=0.;quantum_total=0.;quantum_exact=0.
    success=True;quantum_success=True;hits=[];routes=[]
    groups=[] if best is None else best['groups']
    for index,group in enumerate(groups):
        n=len(group);mask=sum(1<<i for i in group);exact=costs[mask]
        trivial=n<=3;fallback=n>ROUTING_LIMIT
        bank=None;route=None
        if trivial or fallback:
            method='exact_trivial' if trivial else 'classical_size_fallback'
            route=list(orders[mask]);length=exact;atoms=0;feasible_rate=None;hit=None;secs=0.
        elif kind=='random':
            method='uniform_random_permutations'
            start=time.perf_counter()
            candidates=[list(map(int,rng.permutation(group))) for _ in range(shots)]
            values=[route_length(instance,r) for r in candidates]
            winner=int(np.argmin(values));route=candidates[winner];length=values[winner]
            feasible_rate=1.;hit=sum(v<=exact*(1+1e-8) for v in values)/shots;atoms=0;secs=time.perf_counter()-start
        else:
            method=f'{kind}_{mode}'
            bank_path=out/f'{instance["id"]}_cluster{index}_{method}.json'
            bank=simulate(instance,group,kind,mode,seed+index,shots=shots)
            save(bank_path,bank)
            banks.append(bank)
            feasible_rate=bank['feasible_shots']/shots
            hit=sum(p['count'] for p in bank['valid_routes'] if p['length']<=exact*(1+1e-8))/shots
            atoms=bank['atoms'];secs=bank['elapsed_seconds']
            if bank['best']:
                route=bank['best']['route'];length=bank['best']['length']
            else:
                length=None;quantum_success=False
            hits.append(hit)
            quantum_exact+=exact
            if length is not None:
                quantum_total+=length
        if length is None:
            success=False
        else:
            total+=length
            routes.append(route)
        exact_total+=exact
        rows.append(dict(instance=instance['id'],cluster=index,customers=n,group=json.dumps(group),
                         routing_method=method,atoms=atoms,dmm=bool(bank and bank['dmm']),
                         trivial=trivial,classically_routed=fallback,quantum_attempted=bank is not None,
                         quantum_success=bool(bank and bank['best']),exact_tsp=exact,tour_length=length,
                         gap_percent=None if length is None else 100*(length/exact-1),
                         raw_feasibility_rate=feasible_rate,raw_reference_probability=hit,
                         shots=shots if not trivial and not fallback else 0,
                         embedding_error=None if bank is None else bank['embedding_error'],
                         linear_error=None if bank is None else bank['linear_error'],
                         elapsed_seconds=secs))
    if best is None:
        success=False
    nontrivial=sum(not r['trivial'] for r in rows)
    quantum_count=sum(r['quantum_success'] for r in rows)
    fallback_count=sum(r['classically_routed'] for r in rows)
    decomposition=reference['model_optimum_routed_cost']-reference['cvrp_optimum']
    clustering_loss=None if best is None else exact_total-reference['model_optimum_routed_cost']
    routing_loss=total-exact_total if success else None
    if success:
        assert abs(decomposition+clustering_loss+routing_loss-(total-reference['cvrp_optimum']))<1e-6
    metrics=dict(instance=instance['id'],method=f'{kind}_{mode}',seed=seed,track='B',
                 clustering_method=clustering['metrics']['method'],
                 model_gap_percent=clustering['metrics']['model_gap_percent'],
                 clustering_feasibility_rate=clustering['metrics']['feasibility_rate'],
                 model_reference_probability=clustering['metrics']['probability_model_reference'],
                 cvrp_gap_percent=None if best is None else 100*(exact_total/reference['cvrp_optimum']-1),
                 routing_gap_percent=100*(quantum_total/quantum_exact-1) if quantum_success and quantum_exact else None,
                 end_to_end_gap_percent=100*(total/reference['cvrp_optimum']-1) if success else None,
                 decomposition_gap_percent=100*decomposition/reference['cvrp_optimum'],
                 decomposition_loss=decomposition,clustering_loss=clustering_loss,routing_loss=routing_loss,
                 end_to_end_cost=total if success else None,selected_clustering_exact_cost=exact_total if best else None,
                 pipeline_feasible=success,trivial_clusters=sum(r['trivial'] for r in rows),
                 classically_routed_nontrivial_clusters=fallback_count,nontrivial_clusters=nontrivial,
                 quantum_routed_nontrivial_clusters=quantum_count,
                 quantum_nontrivial_fraction=quantum_count/nontrivial if nontrivial else None,
                 quantum_route_raw_joint_reference_probability=float(np.prod(hits)) if hits else None,
                 routing_raw_feasibility_rate=sum(b['feasible_shots'] for b in banks)/sum(b['shots'] for b in banks) if banks else None,
                 reference_epsilon_percent=1e-6,reference_status=reference['status'],
                 routing_peak_atoms=max((b['atoms'] for b in banks),default=0),
                 peak_atoms=max(clustering['metrics']['peak_atoms'],max((b['atoms'] for b in banks),default=0)),
                 clustering_backend_calls=clustering['metrics']['backend_calls'],
                 clustering_backend_shots=clustering['metrics']['backend_shots'],
                 routing_backend_calls=len(banks),routing_backend_shots=sum(b['shots'] for b in banks),
                 dmm_routing=any(b['dmm'] for b in banks),global_detuning_clustering=True,
                 noise=False,modulation=False,backend='QutipBackendV2; state-vector without bond truncation',
                 routing_max_customers=ROUTING_LIMIT,routing_shots_per_cluster=shots,
                 joint_probability_semantics='product of raw conditional routing hit rates; excludes trivial and fallback; conditional on selected clustering')
    return metrics,rows,dict(metrics=metrics,routes=routes,clustering=best,clusters=rows)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tiers',nargs='+',choices=['S','M','L'],default=['S','M','L'])
    parser.add_argument('--seeds',nargs='+',type=int,default=[11,29])
    parser.add_argument('--families',nargs='+',choices=['uniform','heterogeneous'],default=['uniform','heterogeneous'])
    parser.add_argument('--attempts',type=int,default=32)
    parser.add_argument('--shots',type=int,default=ROUTING_SHOTS)
    parser.add_argument('--routing',nargs='+',choices=['edge_global','edge_dmm','position_dmm','random_global'],default=['edge_global','edge_dmm','position_dmm','random_global'])
    args=parser.parse_args()
    if args.attempts<1 or args.shots<1:
        parser.error('attempts and shots must be positive')
    OUT.mkdir(exist_ok=True);(OUT/'instances').mkdir(exist_ok=True);(OUT/'banks').mkdir(exist_ok=True)
    metrics=[];cluster_rows=[];clustering_rows=[]
    for family in args.families:
        for tier in args.tiers:
            for seed in args.seeds:
                instance=(generate if family=='uniform' else generate_heterogeneous)(tier,seed)
                name=instance['id'];print(f'Instance {name}: demands {instance["demands"]}',flush=True)
                save(OUT/'instances'/f'{name}.json',instance)
                reference_start=time.perf_counter()
                reference,costs,orders=references(instance)
                reference['evaluation_seconds']=time.perf_counter()-reference_start
                save(OUT/f'{name}_reference.json',reference)
                for clustering_method in ['slow','random']:
                    _,clustering=evaluate(instance,reference,costs,orders,clustering_method,seed+10000,args.attempts)
                    clustering_rows.append(clustering['metrics'])
                    save(OUT/f'{name}_clustering_{clustering_method}.json',clustering)
                    routes=args.routing if clustering_method=='slow' else ['random_global']
                    for variant in routes:
                        kind,mode=variant.split('_')
                        row,clusters,detail=route_pipeline(instance,reference,clustering,costs,orders,kind,mode,seed+20000,OUT/'banks',args.shots)
                        row['method']=clustering_method+'_'+variant
                        metrics.append(row)
                        for c in clusters:
                            c['pipeline_method']=row['method'];cluster_rows.append(c)
                        save(OUT/f'{name}_{row["method"]}.json',detail)
                        print(f'  {row["method"]}: end-to-end={row["end_to_end_gap_percent"]}, quantum fraction={row["quantum_nontrivial_fraction"]}',flush=True)
                        write_csv(OUT/'results.csv',metrics)
                        write_csv(OUT/'clusters.csv',cluster_rows)
                        write_csv(OUT/'clustering_results.csv',clustering_rows)
    save(OUT/'settings.json',vars(args)|dict(routing_limit=ROUTING_LIMIT,noise=False,modulation=False,clustering_global_only=True))
    print(f'Saved {OUT}',flush=True)
    from .summarize_b import summarize
    from .report_b import build
    summarize()
    build()


if __name__=='__main__':
    main()
