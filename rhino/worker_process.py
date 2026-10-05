"""Standard-library-only launch options for CHESHIRE's external interpreter."""

import os
from pathlib import Path
import subprocess


_PYTHON_RUNTIME_VARIABLES = {
    "PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONEXECUTABLE",
    "__PYVENV_LAUNCHER__", "PYTHONNOUSERSITE",
}


def worker_environment(parent=None):
    """Copy normal OS/Rhino settings, removing Python runtime redirections."""
    source = os.environ if parent is None else parent
    child = {key: value for key, value in source.items() if key.upper() not in _PYTHON_RUNTIME_VARIABLES}
    child["PYTHONNOUSERSITE"] = "1"
    return child


def worker_launch_options(root, request_path, response_path):
    root = Path(root).resolve()
    return {
        "args": [str(root / ".venv/Scripts/python.exe"), "-E", "-s",
                 str(root / "rhino/cheshire_worker.py"), str(request_path), str(response_path)],
        "env": worker_environment(), "cwd": str(root), "shell": False,
        # -E ignores PYTHONNOUSERSITE too, so -s enforces no user site-packages.
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
    }
