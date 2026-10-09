"""Read user-supplied reference PDFs into ignored local review caches."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'output/task29_pdf'))
import pymupdf

FILES=['075-081 (1).pdf','Michael_Hansmeyers_Algorithmic_Architecture_The_T.pdf','mirror.pdf']
DEST=Path(__file__).resolve().parents[1]/'output/task30_references'
DEST.mkdir(parents=True,exist_ok=True)
ledger=[]
for i,name in enumerate(FILES):
    src=Path('C:/Users/USER/Downloads')/name
    doc=pymupdf.open(src);parts=[]
    folder=DEST/f'R{i+1}';folder.mkdir(exist_ok=True)
    for page in doc:
        parts.append(f'\n===== PDF PAGE {page.number+1} =====\n'+page.get_text())
        page.get_pixmap(matrix=pymupdf.Matrix(1.3,1.3)).save(folder/f'page_{page.number+1:02}.png')
    (folder/'text.txt').write_text(''.join(parts),encoding='utf-8')
    record=dict(id=f'R{i+1}',file=str(src),sha256=hashlib.sha256(src.read_bytes()).hexdigest(),pages=len(doc),
                metadata=doc.metadata,cache=str(folder),preview=parts[0][:800])
    ledger.append(record);print(json.dumps(record,ensure_ascii=True),flush=True)
(DEST/'ledger.json').write_text(json.dumps(ledger,indent=2),encoding='utf-8')
