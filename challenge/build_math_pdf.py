"""Build a professionally typeset math PDF from MATH_WRITEUP.md.

Requires Pandoc and Tectonic: brew install pandoc tectonic
Run: python -m challenge.build_math_pdf
The Markdown remains the content source; only equation line breaks are adapted.
"""
from pathlib import Path
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TEMP=ROOT/'tmp'/'pdfs'
OUTPUT=ROOT/'output'/'pdf'/'Pasqal_Mathematical_Writeup.pdf'


def format_equation(match):
    e=match.group(1).strip()
    if e.startswith(r'\sum_{j\in V\setminus\{i\}}z_{ijk}'):
        e=r'''\begin{aligned}
\sum_{j\in V\setminus\{i\}}z_{ijk}&=y_{ik},\\
\sum_{j\in V\setminus\{i\}}z_{jik}&=y_{ik}
\qquad(i\in I,\ k\in\mathcal K).
\end{aligned}'''
    elif e.startswith(r'E_{\rm slack}='):
        e=r'''\begin{aligned}
E_{\rm slack}={}&F(x)+A\sum_i\left(\sum_kx_{ik}-1\right)^2\\
&+B\sum_k\left(\sum_id_ix_{ik}+\sum_\ell a_\ell u_{k\ell}-Q\right)^2.
\end{aligned}'''
    elif e.startswith(r'Q^2+\sum_i'):
        e=r'''\begin{aligned}
Q^2&+\sum_i(d_i^2-2Qd_i)x_{ik}
+2\sum_{i<j}d_id_jx_{ik}x_{jk}\\
&+\sum_\ell(a_\ell^2-2Qa_\ell)u_{k\ell}\\
&+2\sum_{\ell<m}a_\ell a_m u_{k\ell}u_{km}
+2\sum_{i,\ell}d_i a_\ell x_{ik}u_{k\ell}.
\end{aligned}'''
    elif e.startswith(r'E_{\rm pos}='):
        e=r'''\begin{aligned}
E_{\rm pos}={}&\sum_i\widetilde c_{0i}x_{i0}
+\sum_i\widetilde c_{i0}x_{i,n-1}\\
&+\sum_{t=0}^{n-2}\sum_{i\ne j}\widetilde c_{ij}x_{it}x_{j,t+1}\\
&+A_{\rm TSP}\sum_i\left(\sum_t x_{it}-1\right)^2\\
&+A_{\rm TSP}\sum_t\left(\sum_i x_{it}-1\right)^2.
\end{aligned}'''
    elif e.startswith(r'C_{\rm ref}=C^*'):
        e=r'''\begin{aligned}
C_{\rm ref}&=C^*,&
C_{\rm model}&=\sum_{S\in\mathcal G_F^*}L^*(S),\\
C_{\rm shot}&=\sum_{S\in\widehat{\mathcal G}}L^*(S),&
C_{\rm end}&=\sum_{S\in\widehat{\mathcal G}}\widehat L(S).
\end{aligned}'''
    elif e.startswith(r'C_{\rm end}-C_{\rm ref}'):
        e=r'''\begin{aligned}
C_{\rm end}-C_{\rm ref}
={}&\underbrace{C_{\rm model}-C_{\rm ref}}_{\text{decomposition loss}}\\
&+\underbrace{C_{\rm shot}-C_{\rm model}}_{\text{clustering loss}}
+\underbrace{C_{\rm end}-C_{\rm shot}}_{\text{routing loss}}.
\end{aligned}'''
    elif e.startswith(r'D(\{j\},j)'):
        e=r'''\begin{aligned}
D(\{j\},j)&=c_{0j},\\
D(S,j)&=\min_{i\in S\setminus\{j\}}
[D(S\setminus\{j\},i)+c_{ij}].
\end{aligned}'''
    elif e.startswith(r'\delta_{\rm global}=-h_{\min}'):
        e=r'''\begin{aligned}
\delta_{\rm global}&=-h_{\min},&\delta_{\rm DMM}&=-D,\\
\varepsilon_a&=(h_a-h_{\min})/D.
\end{aligned}'''
    # Textual equation tags consume space and are clearer as ordinary qualifiers.
    e=e.replace(r'\tag{coverage equality}',r'\qquad\text{(coverage)}')
    e=e.replace(r'\tag{capacity inequality}',r'\qquad\text{(capacity)}')
    return '$$\n'+e+'\n$$'


def main():
    for executable in ['pandoc','tectonic']:
        if shutil.which(executable) is None:
            raise SystemExit(f'Missing {executable}; install Pandoc and Tectonic first.')
    TEMP.mkdir(parents=True,exist_ok=True);OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    markdown=(ROOT/'challenge'/'MATH_WRITEUP.md').read_text()
    markdown=markdown.split('\n',1)[1].lstrip()
    # Promote numbered content sections for an appropriate PDF contents hierarchy.
    markdown=re.sub(r'^## (\d+\. .+)$',r'# \1',markdown,flags=re.M)
    markdown=markdown.replace('# 19. Mathematical claims and scope checklist', r'\clearpage'+'\n\n# 19. Mathematical claims and scope checklist')
    markdown=markdown.replace('# 20. Separate planetary optimization experiment', r'\clearpage'+'\n\n# 20. Separate planetary optimization experiment')
    markdown=re.sub(r'\$\$(.*?)\$\$',format_equation,markdown,flags=re.S)
    markdown=markdown.replace('| Encoding | Count | S: N=4,K=2,Q=7 | M: N=10,K=3,Q=20 | L: N=15,K=4,Q=30 |', '| Encoding | Count | S | M | L |').replace('|---|---|---:|---:|---:|', '|--------------------------------------|---------------------------------------|-------:|-------:|-------:|')
    markdown=markdown.replace('The 80-atom cap is met', 'Tier parameters are S: $(N,K,Q)=(4,2,7)$; M: $(10,3,20)$; L: $(15,4,30)$.\n\nThe 80-atom cap is met')
    source=TEMP/'math-writeup.md';source.write_text(markdown)
    tex=TEMP/'math-writeup.tex'
    subprocess.run(['pandoc',str(source),'--from=markdown+tex_math_dollars',
                    '--to=latex','--standalone','--toc','--toc-depth=1',
                    '--top-level-division=section','--pdf-engine=tectonic',
                    '-V','documentclass=article','-V','fontsize=11pt','-V','papersize=a4',
                    '-V','geometry=top=25mm,bottom=24mm,left=23mm,right=23mm',
                    '-V','title=Mathematical Write-up',
                    '-V','subtitle=CVRP, Quantum Clustering and Routing',
                    '-V','author=DuQuantum / Pasqal Challenge',
                    '-V','date=Complete derivations and implementation notes',
                    '--include-in-header',str(ROOT/'challenge/pdf/math_header.tex'),
                    '--output',str(tex)],check=True)
    # Keep a formula with its immediately preceding explanatory paragraph.
    latex=tex.read_text()
    latex=re.sub(r'\n\n(?=\\\[)',lambda _: '\n\n'+r'\nopagebreak[4]'+'\n',latex)
    tex.write_text(latex)
    subprocess.run(['tectonic','--keep-logs','--keep-intermediates',str(tex),'--outdir',str(TEMP)],check=True)
    shutil.copyfile(TEMP/'math-writeup.pdf',OUTPUT)
    print(OUTPUT)


if __name__=='__main__':main()
