# IAAC public-process reconstruction / column catalogue

Large data: `E:/CHESHIRE_DATA/terminal_fold_20261011`.
Original assets and kernels are unchanged. Branch: `experiment/terminal-fold-field-20261011`.

The final catalogue uses eight actual G0–G3 sequences. Its main rule is the
published quad split: retain corners, add shared edge midpoints and a face
centre, connect four child quads, then evaluate old and new control vertices.
Inside samples move toward a finite outside grid. Neither wrinkles nor the
initial coordinates are protected in these sequences. The separate radial
inside/outside process and genuine neutral CC are explicit alternatives.

`iaac_input.py --quad` creates the folded input. `--quad --matched-cylinder`
creates the matched cylinder. Both have 6,208 control quads. Input construction
is our existing folded section recipe, not recovered IAAC input code.

```powershell
& C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe experiments/terminal_fold_20261011/iaac_repeat.py --source E:/CHESHIRE_DATA/terminal_fold_20261011/IAAC_QUAD_INPUT/G00 --quad-source --name CAT_N8 --variant n8 --stages 3
```

Variants: `base`, `n4`, `n8`, `three`, `five`, `radial_io`, `cc`.
Use a new `--name` when changing settings. Matching completed stages resume;
mismatched or incomplete outputs are not overwritten. Each stage stores the
authoritative `control_quad.npz` for the next iteration. `geometry.npz`,
`checkpoint.npz` and `gate.ply` contain its explicit face-centre triangle fans.
The renderer and final checker read those exact float64 physical triangles.

`study.py`, `field_follow.py` and their saved outputs retain the earlier
terminal release and protected-field controls. They are not the unrestricted
IAAC catalogue. `FOLD_FIRST` is an implemented but **unexecuted** optional mode.

Sources: [IAAC page](https://www.iaacblog.com/programs/mesh-subdivision/),
[quad split](https://www.iaacblog.com/wp-content/uploads/2020/12/group-4_python-presentation.png),
[nearest-outside loop](https://www.iaacblog.com/wp-content/uploads/2020/12/group-4_python-presentation2.png),
[separate radial loop](https://www.iaacblog.com/wp-content/uploads/2020/12/group-4_python-presentation4.png),
[initial form / later subdivision workflow](https://www.iaacblog.com/wp-content/uploads/2020/12/group-4_python-presentation1.png).

The inspected public diagrams do not provide executable source, the exact 3D
field, movement coefficient, grid spacing, Z adjustment or curve-attractor formula.
Our spherical-power finite Mandelbulb and numeric recipes are declared
reconstructions. No curve attractor, physical sheet solver, thickness,
structural performance or fabrication certification is claimed.
