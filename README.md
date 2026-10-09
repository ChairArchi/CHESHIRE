# Hansmeyer independent implementation: first checkpoint

Branch: `research/hansmeyer-cleanroom` (orphan; no historical tree).
Worktree: `C:/Users/USER/CHESHIRE/cleanroom/hansmeyer`.

```powershell
python -m pip install -r requirements.txt
python run_checkpoint.py
```

The recorded run used only NumPy and Pillow from the existing generic Python
environment: `C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe`.
No historical project module is imported. The renderer currently uses the
Windows Segoe UI font. All OBJ and PNG outputs are in `output/`.

See `docs/HANSMEYER_MIN_IMPLEMENTATION.md` and
`docs/HANSMEYER_MIN_RESULTS.md`. User review is required before expanding
beyond this first checkpoint. No push was performed.
