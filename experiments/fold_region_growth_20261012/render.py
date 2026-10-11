"""Render saved native triangles with the established column material/cameras."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('region_preserved_render',
    HERE.parent/'fold_return_20261012/render.py')
render = importlib.util.module_from_spec(spec); spec.loader.exec_module(render)
render.VIEWS.update(
    front_region=((0, 32, 4.8), (0, 0, 4.8), 4.2),
    side_region=((-32, 0, 4.8), (0, 0, 4.8), 4.2),
    front_shoulder=((0, 32, 7.1), (0, 0, 7.1), 3.8),
    side_shoulder=((-32, 0, 7.1), (0, 0, 7.1), 3.8))

if __name__ == '__main__':
    render.main()
