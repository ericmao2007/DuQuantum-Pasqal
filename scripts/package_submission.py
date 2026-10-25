"""Validate and package the technical submission without credentials or environments."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output'/'submission'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    verification = OUT/'reproduction_check.json'
    if not verification.exists() or json.loads(verification.read_text()).get('status') != 'passed':
        raise SystemExit('Complete the clean-environment reproduction check first.')
    required = ['README.md', 'SUBMISSION_CHECKLIST.md', 'requirements.txt', 'requirements.lock.txt',
                'challenge/MATH_WRITEUP.md', 'challenge/track_b_results/report.pdf',
                'challenge/track_b_results/results.csv', 'challenge/track_b_results/clusters.csv',
                'output/pdf/Pasqal_Mathematical_Writeup.pdf']
    for name in required:
        if not (ROOT/name).is_file():
            raise SystemExit(f'Missing required submission file: {name}')
    files = {name: ROOT/name for name in required}
    for folder in ['challenge', 'docs', 'examples', 'sites', 'scripts']:
        for path in (ROOT/folder).rglob('*'):
            relative = path.relative_to(ROOT)
            if path.is_file() and not any(part.startswith('.') or part == '__pycache__' for part in relative.parts) and path.suffix not in {'.pyc', '.pyo'}:
                files[relative.as_posix()] = path
    files['output/submission/reproduction_check.json'] = verification
    files['REPORT.pdf'] = ROOT/'challenge/track_b_results/report.pdf'
    files['MATHEMATICS.pdf'] = ROOT/'output/pdf/Pasqal_Mathematical_Writeup.pdf'
    manifest = []
    archive = OUT/'DuQuantum_Pasqal_Final.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, path in sorted(files.items()):
            data = path.read_bytes()
            manifest.append(f'{hashlib.sha256(data).hexdigest()}  {name}')
            bundle.writestr(name, data)
        bundle.writestr('MANIFEST.sha256', '\n'.join(manifest)+'\n')
    # Read every member back and validate against the embedded manifest.
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        for line in manifest:
            digest, name = line.split('  ', 1)
            assert hashlib.sha256(bundle.read(name)).hexdigest() == digest, name
    print(f'{archive}: {len(files)} files, {archive.stat().st_size:,} bytes; all SHA-256 checks passed')


if __name__ == '__main__':
    main()
