"""Derive additional aggregate metrics from immutable saved route/shot evidence."""
import csv
import json
import numpy as np
from .track_b import OUT, save, write_csv


def summarize():
    with (OUT/'results.csv').open() as stream:
        rows=list(csv.DictReader(stream))
    updated=[]
    for row in rows:
        path=OUT/f'{row["instance"]}_{row["method"]}.json'
        detail=json.loads(path.read_text());m=detail['metrics'];clusters=detail['clusters']
        instance=json.loads((OUT/'instances'/f'{row["instance"]}.json').read_text())
        reference=json.loads((OUT/f'{row["instance"]}_reference.json').read_text())
        base=json.loads((OUT/f'{row["instance"]}_clustering_{m["clustering_method"]}.json').read_text())['metrics']
        quantum=[c for c in clusters if c['quantum_attempted']]
        stochastic=[c for c in clusters if not c['trivial'] and not c['classically_routed']]
        m['clustering_elapsed_seconds']=base['elapsed_seconds']
        m['routing_elapsed_seconds']=sum(c['elapsed_seconds'] for c in clusters)
        m['reference_evaluation_seconds']=reference.get('evaluation_seconds')
        m['reference_timing_note']='offline reference evaluation, not online quantum decoding'
        m['routing_embedding_error_mean']=float(np.mean([c['embedding_error'] for c in quantum])) if quantum else None
        m['routing_linear_error_max']=max((c['linear_error'] for c in quantum),default=None)
        m['clustering_embedding_error_mean']=base['embedding_error_mean']
        m['total_demand']=sum(instance['demands'])
        m['load_ratio']=m['total_demand']/(instance['vehicles']*instance['capacity'])
        m['largest_demand_ratio']=max(instance['demands'])/instance['capacity']
        m['conditional_raw_routing_feasibility']=float(np.prod([c['raw_feasibility_rate'] for c in quantum])) if quantum else None
        if detail['clustering'] is None:
            m['conditional_end_to_end_reference_probability']=None
        elif m['selected_clustering_exact_cost']>reference['cvrp_optimum']*(1+1e-8):
            m['conditional_end_to_end_reference_probability']=0.
        else:
            m['conditional_end_to_end_reference_probability']=float(np.prod([c['raw_reference_probability'] for c in stochastic]))
        m['conditional_probability_note']='raw independent route draws conditional on the fixed model-selected clustering; not unconditional CVRP or best-of-batch success'
        save(path,detail);updated.append(m)
    write_csv(OUT/'results.csv',updated)
    summary=dict(instances=len({r['instance'] for r in updated}),rows=len(updated),
                 feasible_returned_pipelines=sum(r['pipeline_feasible'] for r in updated),
                 full_random_baseline_rows=sum(r['clustering_method']=='random' for r in updated),
                 quantum_route_failure_rows=sum(not r['pipeline_feasible'] and r['routing_backend_calls']>0 for r in updated),
                 methods={})
    for method in sorted({r['method'] for r in updated}):
        subset=[r for r in updated if r['method']==method]
        summary['methods'][method]=dict(rows=len(subset),returned_feasible=sum(r['pipeline_feasible'] for r in subset),
                                       quantum_calls=sum(r['routing_backend_calls'] for r in subset),
                                       successful_nontrivial_quantum_clusters=sum(r['quantum_routed_nontrivial_clusters'] for r in subset),
                                       classical_size_fallbacks=sum(r['classically_routed_nontrivial_clusters'] for r in subset))
    save(OUT/'summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    summarize()
