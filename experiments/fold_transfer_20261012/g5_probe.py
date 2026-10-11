"""One bounded G5 continuation after the user's finer-facet hypothesis.

Same recipe, two inputs. Start from RETURN_ONLY G4 rather than the visually
weaker protected-field G4. One unchanged-surface resolution control on SPAN.
"""
from pathlib import Path
import importlib.util
import json

# The legacy fractal module is also named study. Do not occupy that import
# name with this transfer driver when loading it as a library.
spec = importlib.util.spec_from_file_location('fold_transfer_driver', Path(__file__).with_name('study.py'))
transfer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transfer)

ROOT = Path('E:/CHESHIRE_DATA/fold_transfer_20261012')


def main():
    for case, label in [('SPAN', 'SPAN'), ('COUNTER', 'COUNTER_MATCHED')]:
        control_record = ROOT/'SPAN_G5_FROM_RETURN/REFINED_ONLY/G05/generation.json'
        if case == 'SPAN' and control_record.exists():
            old = json.loads(control_record.read_text(encoding='utf8'))
            if old['quick_integrity'] != 'PASS' or old['shared_recipe'] != transfer.CFG or Path(old['parent']) != ROOT/'SPAN/RETURN_ONLY/G04':
                raise ValueError('Existing resolution control differs; preserved without overwrite.')
        transfer.late(ROOT, case, ROOT/label/'RETURN_ONLY/G04', 5,
            label=case+'_G5_FROM_RETURN',
            input_source=ROOT/'inputs'/case/'G00',
            save_refinement_control=case == 'SPAN' and not control_record.exists())


if __name__ == '__main__':
    main()
