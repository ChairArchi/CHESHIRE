"""Prepare a fresh replay from tracked frozen inputs, without prior archives."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spatial_activity_study as study


def prepare(directory):
    directory = Path(directory).resolve()
    if not directory.is_relative_to(study.ROOT/"output/task18"):
        raise ValueError("A fresh directory inside output/task18 is required.")
    directory.mkdir(parents=True, exist_ok=False)
    fields = study.read(study.FROZEN/"fields.json")
    if study.digest(study.read(study.FROZEN/"C0.json")) != fields["source_hash"] or study.read(study.FROZEN/"recipes.json") != study.exact_recipes():
        raise ValueError("Frozen source/recipes changed; no replay prepared.")
    cases = [study.case_spec("A", seed, grammar, strategy, 4) for seed in study.SEEDS
        for grammar in ("CC", "DS", "HYBRID") for strategy in ("U", "S", "M", "R", "P")]
    cases += [study.case_spec("A", "A_SHOULDER_PAIR", grammar, "D", 4) for grammar in ("CC", "DS", "HYBRID")]
    study.write(directory/"matrix_A.json", cases)
    study.write(directory/"inputs.json", dict(frozen_inputs="studies/task18",fields_hash=study.digest(fields),
        storage_budget_bytes=study.STORAGE_BUDGET,worker_seconds=120,audit_seconds=30,
        max_vertices=120000,max_faces=120000,max_generation=6,
        replay="Frozen source/fields/recipes reused exactly; no prior output or third-party DLL required"))
    print(directory)


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("directory",type=Path)
    prepare(parser.parse_args().directory)
