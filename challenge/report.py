"""Build English plots and a four-page report from the saved benchmark."""
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'results'


def build():
    rows = list(csv.DictReader((OUT/'results.csv').open()))
    names = list(dict.fromkeys(r['instance'] for r in rows))
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.5))
    x = np.arange(len(names))
    for j, method in enumerate(['fast', 'slow', 'random']):
        lookup = {r['instance']: r for r in rows if r['method'] == method}
        feasible = [100*float(lookup[n]['feasibility_rate']) if n in lookup else np.nan for n in names]
        gaps = [float(lookup[n]['model_gap_percent']) if n in lookup and lookup[n]['model_gap_percent'] else np.nan for n in names]
        axes[0].bar(x+(j-1)*0.25, feasible, width=0.25, label=method)
        axes[1].bar(x+(j-1)*0.25, gaps, width=0.25, label=method)
    for ax in axes:
        ax.set_xticks(x, names, rotation=35)
        ax.legend(fontsize=8)
    axes[0].set(ylabel='Feasible trajectories (%)', ylim=(0, 105))
    axes[1].set(ylabel='Best model gap (%)')
    fig.tight_layout()
    fig.savefig(OUT/'benchmark.png', dpi=170)
    plt.close(fig)

    # Select a saved best-model trajectory; do not optimize a new plan for plotting.
    name = 'L_11' if 'L_11' in names else names[0]
    detail_path = OUT/f'{name}_slow.json'
    detail = json.loads(detail_path.read_text()) if detail_path.exists() else None
    if detail and detail['best_plan']:
        instance = json.loads((ROOT/'instances'/f'{name}.json').read_text())
        xy = np.array(instance['customers'])
        depot = np.array(instance['depot'])
        fig, ax = plt.subplots(figsize=(6, 4))
        for v, route in enumerate(detail['best_plan']['routes']):
            path = np.vstack([depot, xy[route], depot])
            ax.plot(*path.T, marker='o', label=f'Vehicle {v+1}: load {sum(instance["demands"][i] for i in route)}')
        for i, (a, b) in enumerate(xy):
            ax.text(a+1, b+1, str(i), fontsize=8)
        ax.scatter(*depot, marker='*', s=220, color='black', label='Depot', zorder=5)
        ax.set(xlim=(0, 105), ylim=(0, 105), xlabel='x', ylabel='y', title=f'{name}: quantum clusters, exact classical tours')
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(OUT/'example_routes.png', dpi=170)
        plt.close(fig)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyCompact', parent=styles['BodyText'], fontSize=9.5, leading=13, spaceAfter=7))
    styles.add(ParagraphStyle(name='SmallCompact', parent=styles['BodyText'], fontSize=8, leading=10.5, spaceAfter=5))
    story = []
    def p(text, style='BodyCompact'):
        story.append(Paragraph(text, styles[style]))
    def heading(text):
        p(text, 'Heading2')
    def table(data, widths=None):
        t = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#16324f')),
                              ('TEXTCOLOR',(0,0),(-1,0),colors.white),
                              ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                              ('FONTSIZE',(0,0),(-1,-1),8), ('LEADING',(0,0),(-1,-1),11),
                              ('BOTTOMPADDING',(0,0),(-1,-1),6), ('TOPPADDING',(0,0),(-1,-1),6),
                              ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#eef3f7'),colors.white]),
                              ('VALIGN',(0,0),(-1,-1),'TOP')]))
        story.append(t)
        story.append(Spacer(1, 10))
    p('CVRP with Sequential Quantum Subset Sampling', 'Title')
    p('DuQuantum / Pasqal challenge | Track A | Reproducible emulator baseline', 'BodyCompact')
    heading('1. Problem, scope, and headline')
    p('Assign every customer exactly once to at most K identical vehicles, respect each capacity Q, and minimize travel from and back to a fixed depot. We implement quantum clustering and exact classical routing for evaluation. We do not claim Track B quantum routing or quantum advantage.')
    p('Six instances cover the prescribed S/M/L dimensions, with location seeds 11 and 29. The depot is (50,50); all customer coordinates lie in [0,100]^2. Demands are deliberately equal within an instance: 3, 5, and 6 for S, M, and L. A cyclic assignment certifies feasibility and is checked but never used by the sampler.')
    table([['Tier','N / K / Q','Demand','Load ratio','Largest demand / Q'],
           ['S','4 / 2 / 7','3','0.8571','0.4286'],
           ['M','10 / 3 / 20','5','0.8333','0.2500'],
           ['L','15 / 4 / 30','6','0.7500','0.2000']])
    p('Instead of one atom per customer/vehicle assignment, each quantum call selects a subset for one vehicle from a seeded window of at most eight remaining customers. Vehicles reuse the register sequentially. Invalid measured choices terminate a trajectory; there is no classical repair or certificate fallback. The last vehicle receives the remainder if it fits.')
    p('The slow pulse reaches the exact model optimum on both S instances. M/L solutions remain suboptimal. The sample shows improved model gaps relative to the random proposal baseline, but route quality does not improve uniformly. These are small, finite-bank experiments without statistical-significance claims.')
    heading('Reproduction and evidence')
    p('Run: <font face="Courier">python -m challenge.run</font> in the pinned Python 3.11 environment. README.md also provides a single uv command. Results include CSV metrics, per-trajectory outcomes, instance certificates, exact references, realized coordinates, target couplings, pulse serialization, and raw conditional shot banks.')
    story.append(PageBreak())
    heading('2. Derivation and variable accounting')
    p('Let x_iv indicate whether customer i is assigned to vehicle v. Exact coverage is sum_v x_iv=1; capacity is sum_i d_i x_iv&lt;=Q. Full route arcs satisfy customer in/out degree, depot flow with at most one departure, and customer-subset subtour inequalities. MODEL.md states the full constrained CVRP.')
    p('Our clustering objective is F(G)=sum over groups S of [lambda |S|^2 + sum over i&lt;j in S of w_ij], where lambda=0.15 and w_ij is Euclidean distance divided by 100 sqrt(2). This balances group size and geographic compactness, but ignores depot travel and tour order.')
    p('The textbook exact penalty adds A sum_i(sum_v x_iv-1)^2 and B sum_v(sum_i d_i x_iv + slack_v-Q)^2. Encode slack with ceil(log2(Q+1)) bits. Since F is nonnegative and violations have integer residual at least one, A=B=F(certificate)+1 suffices algebraically. The resulting variable-specific linear terms are generally incompatible with global detuning.')
    table([['Encoding','S','M','L'],['Direct N^2 K','32','300','900'],['Assignment NK','8','30','60'],['Assignment + slack','14','45','80'],['Implemented peak atoms','4','8','8']],[245,70,70,70])
    p('This reduction changes the algorithm rather than providing an equivalent compact encoding. It trades peak atoms for repeated preparations, window restrictions, greedy decisions, and rejection. Backend calls and shot counts are reported separately.')
    p('For remaining customer set R and L vehicles, choose mu=2 lambda |R|/L. The unconstrained subset target is E(s)=4[lambda (sum_i s_i)^2 + sum_i&lt;j w_ij s_i s_j - mu sum_i s_i]. Therefore h_i=4(lambda-mu) is shared and J_ij=4(2lambda+w_ij) is positive. Set final global detuning to -h_i. Capacity is not exactly encoded by this energy.')
    p('With equal demand d, capacity becomes B=floor(Q/d). Accept a subset only if its size is at most B and the remaining count is at most (L-1)B. This gives a constant-time completion-existence check for this restricted family; it is not a general bin-packing solution. Later random choices may still fail.')
    heading('Embedding and pulse')
    p('Fit all pair couplings with constrained SLSQP (120 iterations, ftol=1e-7). Impose separation &gt;=5.001 um and radius &lt;=37.999 um. Report ||J_real-J_target|| / ||J_target|| over unordered pairs. All physical long-range interactions remain. Global-detuning-only pulses use Omega=6 rad/us, initial delta=-12 rad/us, and fast/slow durations 2000/5200 ns. Every sequence is checked by Pulser. No DMM or hardware modulation is enabled.')
    story.append(PageBreak())
    heading('3. Results and reference checks')
    p('Each method has 32 full trajectory attempts per instance. A conditional quantum simulation supplies a 1000-shot bank; trajectories resample from cached banks. Feasibility and reference probability use all attempts as denominator. Failures have no gap. Quantum methods spend additional bank shots; equal trajectory budgets are not equal compute budgets.')
    data = [['Instance','Method','Feasible %','Model gap %','CVRP gap %']]
    def fmt(v):
        return '-' if v == '' else f'{float(v):.2f}'
    for r in rows:
        data.append([r['instance'],r['method'],f'{100*float(r["feasibility_rate"]):.1f}',fmt(r['model_gap_percent']),fmt(r['cvrp_gap_percent'])])
    table(data,[72,65,95,100,100])
    p('Model and CVRP gaps select the best feasible trajectory at their respective objective levels. A separate CSV column retains the CVRP gap of the model-selected trajectory. Epsilon for reaching the model reference is 0.000001 percent. Vehicle relabelings are canonicalized.', 'SmallCompact')
    p('References enumerate every feasible subset and its exact depot TSP, then solve the unlabeled partition problem by exact dynamic programming. On S, independent assignment enumeration and constrained CPLEX set-partition models agree with both model and CVRP optima. CPLEX uses 30 seconds, one thread, zero relative MIP gap. Reference work is offline evaluation, never part of quantum decoding.', 'SmallCompact')
    story.append(PageBreak())
    heading('4. Interpretation and what did not work')
    story.append(Image(str(OUT/'benchmark.png'), width=480, height=153))
    p('The first embedding attempt minimized log-coupling residuals. It produced large relative coupling errors and zero L-tier feasibility in this sample. Replacing that objective with squared actual-coupling residuals improved the fit and restored feasible L trajectories. The exploratory CSV is retained in experiments/log_loss_baseline.csv; it is not mixed into the final benchmark.')
    p('Even after correction, planar positive distance couplings do not reproduce arbitrary target matrices. Final coupling errors remain material. A slower sweep cannot correct the wrong final Hamiltonian. The report therefore attributes no improvement solely to adiabaticity.')
    p('The clustering surrogate and CVRP disagree: on M_11, the slow pulse improves the model gap over random proposals but worsens the evaluated route gap. This is decomposition error, not a reason to hide the random baseline. The eight-customer window adds another restriction and can exclude good early choices.')
    p('Finite shared shot banks introduce sampling uncertainty; 32 trajectories are insufficient for a robust advantage claim. No noise, modulation response, calibrated trap layout, or hardware execution is modeled. Equal demands simplify capacity checks; heterogeneous demands need a revised encoding or a clearly budgeted feasibility mechanism. Classical routing and exact references may dominate runtime, and are reported as evaluation costs.')
    heading('Next experiments and ownership')
    p('Useful next work: multiple sampler seeds per fixed instance, more trajectories with uncertainty estimates, window-size ablation, heterogeneous-demand instances, and improved native embeddings. Track B would additionally require two routing encodings and genuinely quantum routing of nontrivial clusters; none is claimed here.')
    p('AI assisted formulation, code, debugging, plots, and writing. Executable tests check certificates, capacity penalties, independent exact references, saved feasible assignments, and actual geometric/pulse evidence. Team members must review and explain every submitted claim.')
    p('Sources: Pasqal challenge v3.0, 24 October 2026 (user-provided). Andrew Lucas, Ising formulations of many NP problems, Frontiers in Physics 2 (2014), doi:10.3389/fphy.2014.00005. Pulser source and device definitions: github.com/pasqal-io/Pulser.', 'SmallCompact')
    def footer(canvas, doc):
        canvas.setFont('Helvetica',8)
        canvas.setFillColor(colors.HexColor('#526478'))
        canvas.drawString(44,24,'DuQuantum Pasqal | Track A | Emulator results')
        canvas.drawRightString(A4[0]-44,24,str(doc.page))
    SimpleDocTemplate(str(OUT/'report.pdf'),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=36,bottomMargin=38).build(story,onFirstPage=footer,onLaterPages=footer)
    print(f'Built {OUT / "report.pdf"}')


if __name__ == '__main__':
    build()
