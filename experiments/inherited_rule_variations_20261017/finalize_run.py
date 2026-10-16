"""Record the completed bounded experiment without adopting a new main model."""
from pathlib import Path
import hashlib
import json


def read(path):return json.loads(path.read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=Path('E:/CHESHIRE_DATA/experiments/inherited_rule_variations_20261017')
    exports=Path('E:/CHESHIRE_DATA/exports/20261017/COLUMN_INHERITED_RULE_VARIATIONS')
    qa_path=exports/'models/INHERITED_EXPORT_AND_QA.json'
    delivery_path=exports/'REVIEW/DELIVERY_MANIFEST.json'
    qa,delivery=read(qa_path),read(delivery_path)
    if not qa['passed'] or qa['completed_count']!=7 or not delivery['passed']:
        raise ValueError('Incomplete actual outputs.')
    selection=read(root/'SELECTION.json')
    result=dict(status='COMPLETED_PROTOTYPE_NOT_ADOPTED',baseline='I00',variant_count=6,
        original_SPAN_input_exact_all_cases=True,baseline_original_G4_exact=True,
        existing_operator_sources_unchanged=True,
        varied_controls=['existing return positions','unequal return spans and widths',
            'existing return directions and sweeps','existing root/sidewall selection positions',
            'regional existing Task36 subdivision point coefficients w3/w4/w1'],
        new_seed_or_shape_grammar=False,late_detail_tuning=False,comparison_stage='G04_NEUTRAL',
        source_repo=str(Path(__file__).resolve().parents[2]),
        independent_QA=dict(path=str(qa_path),sha256=sha(qa_path)),
        review_delivery=dict(path=str(delivery_path),sha256=sha(delivery_path)),
        gallery=str(exports/'REVIEW/review.html'),
        comparison_board=str(exports/'REVIEW/comparison_board.png'),
        algorithm_archive=str(exports/'REVIEW/algorithm_source.zip'),
        recommendations=selection['preferred_candidates'],user_adopted=False,
        main_model_replaced=False,self_intersection_or_manufacturing_certified=False)
    path=root/'RUN_RESULT.json'
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(path)


if __name__=='__main__':main()
