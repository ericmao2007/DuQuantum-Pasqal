"""Two TSP QUBOs, legal analog execution, and strict route decoding."""
from dataclasses import replace
from itertools import combinations
import time
import numpy as np
from scipy.spatial.distance import pdist
import pulser
from pulser.channels import DMM
from pulser.backend import BitStrings
from pulser.backends import QutipBackendV2
from pulser_simulation import QutipConfig
from .quantum import embed

PENALTY = 10.0
SCALE = 0.1
ROUTING_LIMIT = 4
ROUTING_SHOTS = 2000


def distances(instance, group):
    points = np.array([instance['depot']] + [instance['customers'][i] for i in group])
    return np.linalg.norm(points[:, None] - points[None, :], axis=-1)


def route_length(instance, route):
    points = np.array([instance['depot']] + [instance['customers'][i] for i in route] + [instance['depot']])
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


def encoding(instance, group, kind):
    """Return canonical h,J,constant; energy equals normalized length + penalties."""
    n = len(group)
    cost = distances(instance, group) / np.sqrt(20000)
    if kind == 'position':
        variables = [(i, t) for i in range(n) for t in range(n)]
        h, j, constant = np.zeros(n*n), np.zeros((n*n,n*n)), 2*n*PENALTY
        index = {v: p for p, v in enumerate(variables)}
        # One customer per position and one position per customer.
        for family in [[index[i,t] for t in range(n)] for i in range(n)] + [[index[i,t] for i in range(n)] for t in range(n)]:
            for a in family:
                h[a] -= PENALTY
            for a,b in combinations(family,2):
                j[a,b] += 2*PENALTY
                j[b,a] += 2*PENALTY
        for i in range(n):
            h[index[i,0]] += cost[0,i+1]
            h[index[i,n-1]] += cost[i+1,0]
            for k in range(n):
                if i == k:
                    continue
                for t in range(n-1):
                    a,b=index[i,t],index[k,t+1]
                    j[a,b] += cost[i+1,k+1]
                    j[b,a] += cost[i+1,k+1]
    elif kind == 'edge':
        variables = list(combinations(range(n+1),2))
        m=len(variables)
        h,j,constant=np.zeros(m),np.zeros((m,m)),4*(n+1)*PENALTY
        for a,(i,k) in enumerate(variables):
            h[a] += cost[i,k]
        for vertex in range(n+1):
            family=[p for p,e in enumerate(variables) if vertex in e]
            for a in family:
                h[a] -= 3*PENALTY
            for a,b in combinations(family,2):
                j[a,b] += 2*PENALTY
                j[b,a] += 2*PENALTY
        # For n<=4, a simple degree-two graph on <=5 vertices is one cycle.
        # At >=6 vertices disconnected cycles require subtour constraints.
        if n > ROUTING_LIMIT:
            raise ValueError('Edge encoding is exact here only for at most four customers')
    else:
        raise ValueError(kind)
    return dict(kind=kind, group=list(group), variables=variables, h=h, J=j, constant=constant)


def decode(bits, spec):
    group=spec['group'];n=len(group)
    chosen=[spec['variables'][i] for i,b in enumerate(bits) if int(b)]
    if spec['kind']=='position':
        if len(chosen)!=n:
            return None
        if len({i for i,t in chosen})!=n or len({t for i,t in chosen})!=n:
            return None
        return [group[i] for i,t in sorted(chosen,key=lambda x:x[1])]
    adjacency={v:[] for v in range(n+1)}
    for a,b in chosen:
        adjacency[a].append(b);adjacency[b].append(a)
    if any(len(v)!=2 for v in adjacency.values()):
        return None
    walk=[0];previous=-1;current=0
    while True:
        options=[v for v in adjacency[current] if v!=previous]
        nxt=min(options)
        if nxt==0:
            break
        if nxt in walk:
            return None
        walk.append(nxt);previous,current=current,nxt
    if len(walk)!=n+1:
        return None
    return [group[i-1] for i in walk[1:]]


def energy(bits,spec):
    x=np.asarray(list(bits),dtype=float)
    return float(spec['constant']+spec['h']@x+np.sum(np.triu(spec['J'],1)*np.outer(x,x)))


def simulate(instance, group, kind, mode, seed, shots=ROUTING_SHOTS):
    start=time.perf_counter()
    spec=encoding(instance,group,kind)
    h,j=SCALE*spec['h'],SCALE*spec['J']
    xy,error,iterations=embed(j)
    reg=pulser.Register.from_coordinates(xy,prefix='r',center=False)
    dmm=mode=='dmm'
    device=pulser.AnalogDevice
    if dmm:
        device=replace(device,name='AnalogDeviceEmulationDMM',dmm_objects=(DMM(clock_period=4,min_duration=16,max_duration=6000,bottom_detuning=-125.663706,total_bottom_detuning=-10000.),))
    seq=pulser.Sequence(reg,device)
    seq.declare_channel('drive','rydberg_global')
    baseline=float(h.min() if dmm else h.mean())
    delta=-baseline
    duration=5200
    if dmm:
        spread=float(np.ptp(h))
        weights=np.zeros(len(h)) if spread<1e-12 else (h-h.min())/spread
        seq.config_detuning_map(reg.define_detuning_map({q:float(w) for q,w in zip(reg.qubit_ids,weights)}),'dmm_0')
        # Ramp local penalty offsets together with the global sweep.
        seq.add_dmm_detuning(pulser.CompositeWaveform(pulser.ConstantWaveform(800,0),pulser.RampWaveform(3600,0,-spread),pulser.ConstantWaveform(800,-spread)),'dmm_0')
    seq.add(pulser.Pulse.ConstantDetuning(pulser.RampWaveform(800,0,6),-12,0),'drive',protocol='no-delay')
    seq.add(pulser.Pulse.ConstantAmplitude(6,pulser.RampWaveform(3600,-12,delta),0),'drive',protocol='no-delay')
    seq.add(pulser.Pulse.ConstantDetuning(pulser.RampWaveform(800,6,0),delta,0),'drive',protocol='no-delay')
    assert seq.get_duration()==duration
    np.random.seed(seed)
    cfg=QutipConfig(observables=[BitStrings(num_shots=shots,evaluation_times=[1.])])
    counts=dict(QutipBackendV2(seq,config=cfg).run().final_bitstrings)
    valid=[]
    for bits,count in counts.items():
        route=decode(bits,spec)
        if route is not None:
            valid.append(dict(bits=bits,count=count,route=route,length=route_length(instance,route)))
    best=min(valid,key=lambda p:p['length']) if valid else None
    physical_h=h if dmm else np.full(len(h),baseline)
    return dict(kind=kind,mode=mode,dmm=dmm,group=list(group),variables=spec['variables'],atoms=len(h),shots=shots,seed=seed,
                duration_ns=duration,coordinates_um=xy.tolist(),target_h=h.tolist(),target_J=j.tolist(),
                constant=SCALE*spec['constant'],linear_error=float(np.linalg.norm(physical_h-h)/np.linalg.norm(h)),
                embedding_error=error,embedding_iterations=iterations,counts=counts,
                feasible_shots=sum(p['count'] for p in valid),best=best,valid_routes=valid,
                sequence=seq.to_abstract_repr(),elapsed_seconds=time.perf_counter()-start,
                backend='QutipBackendV2',noise=False,modulation=False,mimic_qpu=False,
                min_separation_um=float(min(pdist(xy))),max_radius_um=float(max(np.linalg.norm(xy,axis=1))))
