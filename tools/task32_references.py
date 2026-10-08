"""Download bounded public research documents, no installs or upstream code import."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import urllib.request
from task32_research import ROOT, sha, write_new

SOURCES = {
    'field_grammar.pdf': 'https://peterwonka.net/Publications/pdfs/2011.TVCG.Li.FieldGuidedGrammar.TechnicalReport.pdf',
    'shell_growth.pdf': 'https://www.cs.mcgill.ca/~kry/pubs/gi2019/Reaction_Diffusion_Shell_Growth.pdf',
    'multiresolution.pdf': 'https://hhoppe.com/mra.pdf',
    'developability_LICENSE.txt': 'https://raw.githubusercontent.com/odedstein/DevelopabilityOfTriangleMeshes/master/LICENSE.txt',
    'geometry_central_LICENSE.txt': 'https://raw.githubusercontent.com/nmwsharp/geometry-central/master/LICENSE',
    'ready_README.txt': 'https://raw.githubusercontent.com/GollyGang/ready/gh-pages/README.md',
}


def extract_existing():
    # Existing Task29's isolated optional reader is reused read-only; no change
    # to the active research environment or its installed packages.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'output/task29_pdf'))
    import pymupdf
    records = []
    for path in sorted((ROOT/'references').glob('*.pdf')):
        with pymupdf.open(path) as document:
            content = '\n'.join(f'\n--- PAGE {i+1} ---\n'+page.get_text() for i,page in enumerate(document))
            text_path = path.with_suffix('.extracted.txt')
            with text_path.open('x', encoding='utf-8') as stream:
                stream.write(content)
            records.append(dict(name=path.name, pdf_sha256=sha(path), pages=len(document),
                text_sha256=sha(text_path), reader_version=pymupdf.VersionBind,
                review_status='Extracted; researcher review logged separately'))
    write_new(ROOT/'references/extraction_manifest.json', records)
    print(records)


if __name__ == '__main__' and '--extract' in sys.argv:
    extract_existing()
    raise SystemExit(0)

if __name__ == '__main__':
    out = ROOT/'references'
    out.mkdir(parents=True, exist_ok=False)
    records = []
    for name, url in SOURCES.items():
        record = dict(name=name, url=url, UTC=datetime.now(timezone.utc).isoformat(),
                      code_copied_or_executed=False)
        try:
            request = urllib.request.Request(url, headers={'User-Agent':'CHESHIRE research document retrieval'})
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read(40*1024**2+1)
            if len(data) > 40*1024**2:
                raise ValueError('Document exceeds bounded 40MiB retrieval.')
            if name.endswith('.pdf') and not data.startswith(b'%PDF'):
                raise ValueError('Expected PDF, not HTML/error body.')
            path = out/name
            with path.open('xb') as stream:
                stream.write(data)
            record.update(status='downloaded', bytes=len(data), sha256=sha(path))
            if name.endswith('.pdf'):
                import fitz
                with fitz.open(path) as document:
                    text = '\n'.join(f'\n--- PAGE {i+1} ---\n'+page.get_text() for i,page in enumerate(document))
                    with path.with_suffix('.extracted.txt').open('x',encoding='utf-8') as stream:
                        stream.write(text)
                    record.update(pages=len(document), extracted_sha256=sha(path.with_suffix('.extracted.txt')),
                                  reviewed_pages='Pending explicit researcher review; extraction is not review.')
        except Exception as exc:
            record.update(status='failed', error=str(exc))
        records.append(record)
        print(name, record['status'], record.get('bytes',record.get('error')), flush=True)
    write_new(out/'manifest.json', records)
