"""Build the four-page final Track B report and comparison plots."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from .track_b import OUT


def build():
    with (OUT/'results.csv').open() as stream:
        rows=list(csv.DictReader(stream))
    summary=json.loads((OUT/'summary.json').read_text())
    with (OUT/'clusters.csv').open() as stream:
        clusters=list(csv.DictReader(stream))
    fig,axes=plt.subplots(1,2,figsize=(10,3.2))
    variants=['edge_global','edge_dmm','position_dmm']
    for ax,field,label in [(axes[0],'raw_feasibility_rate','Valid raw routing shots (%)'),(axes[1],'gap_percent','Best valid routing gap (%)')]:
        data=[]
        for variant in variants:
            matching=[r for r in clusters if r['routing_method']==variant and r[field]!='']
            values=[float(r[field])*(100 if field=='raw_feasibility_rate' else 1) for r in matching]
            data.append(float(np.mean(values)) if values else np.nan)
        ax.bar(variants,data,color=['#4c78a8','#f58518','#e45756'])
        ax.tick_params(axis='x',rotation=15);ax.set_ylabel(label)
        if field=='raw_feasibility_rate':
            ax.set_yscale('symlog',linthresh=0.1)
    fig.tight_layout();fig.savefig(OUT/'routing_comparison.png',dpi=170);plt.close(fig)

    # Visualize an actual completed nontrivial quantum-routing solution.
    candidates=[r for r in rows if r['method']=='slow_edge_dmm' and r['pipeline_feasible']=='True' and int(r['quantum_routed_nontrivial_clusters'])>0]
    if candidates:
        chosen=candidates[-1]
        detail=json.loads((OUT/f'{chosen["instance"]}_{chosen["method"]}.json').read_text())
        instance=json.loads((OUT/'instances'/f'{chosen["instance"]}.json').read_text())
        xy=np.array(instance['customers']);depot=np.array(instance['depot'])
        fig,ax=plt.subplots(figsize=(6,4))
        for v,route in enumerate(detail['routes']):
            path=np.vstack([depot,xy[route],depot]);ax.plot(*path.T,marker='o',label=f'Vehicle {v+1}')
        for i,(x,y) in enumerate(xy):
            ax.text(x+1,y+1,str(i),fontsize=7)
        ax.scatter(*depot,marker='*',s=180,color='black',label='Depot',zorder=10)
        ax.set(title=f'{chosen["instance"]}: measured edge/DMM tours + labeled fallback',xlabel='x',ylabel='y',xlim=(0,105),ylim=(0,105))
        ax.legend(fontsize=7);fig.tight_layout();fig.savefig(OUT/'end_to_end_routes.png',dpi=170);plt.close(fig)

    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyC',parent=styles['BodyText'],fontSize=9.2,leading=12.3,spaceAfter=7))
    styles.add(ParagraphStyle(name='SmallC',parent=styles['BodyText'],fontSize=7.5,leading=10,spaceAfter=5))
    story=[]
    def p(text,style='BodyC'):story.append(Paragraph(text,styles[style]))
    def h(text):p(text,'Heading2')
    def table(data,widths=None):
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#16324f')),('TEXTCOLOR',(0,0),(-1,0),colors.white),
                              ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),7.5),
                              ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
                              ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#eef3f7'),colors.white])]))
        story.append(t);story.append(Spacer(1,8))
    p('CVRP: Quantum Clustering and Routing','Title')
    p('DuQuantum / Pasqal | Track B | Final emulator evidence','BodyC')
    h('1. Completed scope and reproducible protocol')
    p('The pipeline assigns customers to capacity-limited vehicles, quantum-routes eligible nontrivial clusters, merges tours, and evaluates the original CVRP objective. It implements two TSP encodings and labels global-only versus emulator-only DMM controls. It does not claim hardware execution, an exact analog mapping, or quantum advantage.')
    p(f'The benchmark contains {summary["instances"]} instances and {summary["rows"]} method rows: all prescribed S/M/L tiers, seeds 11 and 29, and both uniform and heterogeneous demand families. Coordinates are seeded uniform samples in [0,100]^2; depot=(50,50). Varied demands are reduced only as needed to make a checked cyclic feasibility certificate. The optimizer never reads the certificate.')
    p('Quantum clustering uses at most eight atoms per sequential call, 32 complete trajectories, and no repair. It rejects measured capacity violations and necessary remaining-load-bound failures. Under heterogeneous demands the remaining-load test is not sufficient for packability; final validation still decides feasibility. The last vehicle receives the remainder.')
    p('For each best-model clustering, compare edge/global, edge/DMM, position/DMM, and 2000 random valid permutations per eligible cluster. Also run random clustering plus random routing. Reference solvers never choose a quantum assignment or replace a failed quantum route.')
    table([['Cluster size','Routing action','Quantum metric treatment'],['n <= 3','Exact trivial route','Excluded from routing gap/hits'],['n = 4','Execute both encodings','Keep valid and invalid shots'],['n > 4','Exact classical size fallback','Excluded; reduces quantum coverage']],[75,170,260])
    p('A failed n=4 quantum batch remains a failed end-to-end method. There is no post-failure classical fallback. Returned best-of-batch feasibility differs from raw shot feasibility. Conditional routing-hit probabilities do not constitute unconditional CVRP success probabilities.')
    h('Reproduction and audit trail')
    p('Run <font face="Courier">python -m challenge.track_b</font> in the pinned Python 3.11 environment; README supplies a one-command uv form. Evidence includes instance certificates, exact references, per-trajectory clustering, per-cluster CSV, serialized pulses, all raw routing counts, native coordinates and coefficients, gaps and absolute losses. Historical Track A evidence is preserved separately.')
    story.append(PageBreak())
    h('2. Models, variables, and physical controls')
    p('CVRP constraints enforce one vehicle per customer, load <=Q, one depot trip per used vehicle, and one customer visit without subtours. Clustering minimizes sum over groups [0.15 |S|^2 + sum of normalized within-group distances]. This surrogate ignores depot tours, so model and CVRP optima can disagree. Full derivations are in MODEL.md and TRACK_B_MODEL.md.')
    table([['Encoding / tier','S','M','L'],['Direct customer/vehicle/position','32','300','900'],['Assignment + binary slack','14','45','80'],['Sequential clustering peak','4','8','8']],[275,70,70,70])
    p('For routing, normalize each travel edge by 100 sqrt(2) and set A=10. At n=4 every valid tour costs <=5 normalized units, so an integer constraint violation cannot improve the exact target optimum. Exhaustive tests check all target bitstrings independently of the simulator.')
    p('<b>Position:</b> x_it indicates customer i at position t. Cost is depot-to-first + consecutive customer edges + last-to-depot, plus A times squared row and column one-hot violations. There are n^2 variables: 16 for four customers; 24 bitstrings encode the 12 undirected tours. Pair coefficients are positive; linear terms differ at route endpoints.')
    p('<b>Edge:</b> one e_ij per unordered depot/customer pair; minimize sum c_ij e_ij + A sum_v(degree_v-2)^2. There are n(n+1)/2 variables: 10 for four customers, with 12 valid bitstrings. Degree-two is a complete TSP encoding here only because <=5 vertices cannot contain two disjoint simple cycles. Larger instances would need subtour constraints; this code refuses to use the degree-only model beyond its valid range.')
    p('Fit physical couplings (C6/hbar)/r^6 to the full positive target matrix, including unwanted couplings at desired zeros. SLSQP enforces separation >=5 um and radius <=38 um; all actual Pulser sequences retain long-range interactions. Report pairwise relative norm error, linear residual, atom count, and shot cost. Routing uses at most 16 atoms, full state-vector QutipBackendV2, and no MPS truncation.')
    p('For variable linear h_i, global-only control projects to their mean. DMM runs instead set global delta=-min(h), DMM delta=-range(h), and weights (h_i-min(h))/range(h). Thus DMM only raises selected excitation costs, with weights in [0,1] and nonpositive detuning. These are explicitly emulator-only controls, not a QPU claim.')
    p('Both routing variants use a 5200 ns pulse (800/3600/800 ns), Omega_max=6 rad/us, initial global delta=-12 rad/us, and zero final drive. DMM ramps concurrently during the sweep. No noise, modulation response, or calibrated trap layout is assumed. Global and DMM results are separately labeled.')
    story.append(PageBreak())
    h('3. End-to-end results and exact references')
    p('Primary edge/DMM results below use the model-selected quantum clustering. Gaps are percentages; Q coverage is the fraction of nontrivial clusters successfully quantum-routed, including classical size fallbacks in its denominator. A dash is undefined. U/H denotes uniform/heterogeneous demands. Random and encoding comparisons are retained in the full CSV.')
    data=[['Instance','Cluster\nvalid %','Model\ngap','Route\ngap','End-to-end\ngap','Q coverage']]
    def fmt(v):return '-' if v=='' else f'{float(v):.2f}'
    for r in rows:
        if r['method']!='slow_edge_dmm':continue
        label=r['instance'].replace('_heterogeneous_','_H').replace('_11','_U11').replace('_29','_U29') if 'heterogeneous' not in r['instance'] else r['instance'].replace('_heterogeneous_','_H')
        data.append([label,f'{100*float(r["clustering_feasibility_rate"]):.1f}',fmt(r['model_gap_percent']),fmt(r['routing_gap_percent']),fmt(r['end_to_end_gap_percent']),'-' if r['quantum_nontrivial_fraction']=='' else f'{100*float(r["quantum_nontrivial_fraction"]):.0f}%'])
    table(data,[80,80,65,65,100,85])
    p('Reference values are proven optima from exact feasible-subset partition dynamic programming. Subset tours use Held-Karp. S references are independently cross-checked against all assignments and direct constrained CPLEX (30 s, one thread, zero relative MIP gap). Vehicle-label symmetry is removed; optimal partition counts are saved.')
    p('With C_ref=CVRP optimum, C_model=exact-routed model optimum, C_shot=exact-routed selected clustering, and C_end=actual merged routes, the code asserts: C_end-C_ref = (C_model-C_ref) + (C_shot-C_model) + (C_end-C_shot). These are decomposition, clustering, and routing losses. Clustering loss can be negative and is not clipped.')
    p('Routing gap excludes trivial and classical fallback clusters. If any eligible quantum route fails, its aggregate routing/end-to-end gap is undefined. Raw reference-hit rates count invalid shots in the denominator, with epsilon=0.000001 percent. The product of conditional hit rates is clearly labeled; it is not the success probability of selecting the best of 2000 shots.')
    story.append(PageBreak())
    h('4. Encoding comparison and what did not work')
    story.append(Image(str(OUT/'routing_comparison.png'),width=490,height=157))
    data=[['Routing variant','Returned feasible','Quantum calls','Successful Q clusters']]
    for name in ['slow_edge_global','slow_edge_dmm','slow_position_dmm']:
        s=summary['methods'].get(name)
        if s:data.append([name.replace('slow_',''),f'{s["returned_feasible"]}/{s["rows"]}',str(s['quantum_calls']),str(s['successful_nontrivial_quantum_clusters'])])
    table(data,[155,115,110,125])
    p('A correct target QUBO did not guarantee a useful physical embedding. The position formulation can yield no valid route at all despite passing exhaustive target-energy tests. All such failures remain visible. Embedding distortion, unwanted couplings, finite-time evolution, and limited shots are not repaired by invoking the word adiabatic.')
    p('Global-only edge projection discards route-specific linear costs. DMM restores those coefficients, but does not repair pair couplings. Similar global/DMM best tours in a small sample do not establish equal Hamiltonians or a benefit from DMM. The random valid-permutation baseline is particularly strong: at four customers there are only 12 undirected tours, so 2000 samples generally find the exact route.')
    p('Nontrivial clusters larger than four are classically routed. Their contribution remains in end-to-end cost and reduces quantum coverage. Trivial-only S results validate the pipeline but provide no evidence for quantum routing. Heterogeneous demands add genuine packing difficulty; a low or zero clustering feasibility rate is reported, not hidden behind the certificate.')
    p('Costs include classical embedding, conditional-shot-bank construction, best-sample selection, trivial/fallback routing, and offline exact references. Shared finite clustering banks introduce uncertainty. Two instance seeds are not evidence of statistical advantage. Noise and actual QPU behavior are outside the present evidence.')
    p('<b>AI and review:</b> AI assisted derivation, implementation, debugging, experiments, tests, and writing. Tests exhaustively verify both four-customer QUBOs, compare Held-Karp against permutations, validate certificates and saved routes, check physical envelopes, and assert the three-loss identity. Team members must review and be able to explain the submission.')
    p('Sources: supplied Pasqal challenge v3.0 (24 October 2026); Andrew Lucas, Ising formulations of many NP problems, Frontiers in Physics 2 (2014), doi:10.3389/fphy.2014.00005; installed Pulser 1.9.1 device and simulation definitions. Full formulas and settings are in TRACK_B_MODEL.md and saved JSON evidence.','SmallC')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#526478'))
        canvas.drawString(40,23,'DuQuantum Pasqal | Track B | Emulators only');canvas.drawRightString(A4[0]-40,23,str(doc.page))
    SimpleDocTemplate(str(OUT/'report.pdf'),pagesize=A4,leftMargin=40,rightMargin=40,topMargin=32,bottomMargin=37).build(story,onFirstPage=footer,onLaterPages=footer)
    print(f'Built {OUT / "report.pdf"}')


if __name__=='__main__':build()
