"""One ignored local preference; no environment scan or DLL copying."""

from pathlib import Path

from exchange import read_json, write_json_atomic


def valid_mola_path(root, value):
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        return None
    path = path.resolve()
    if path.suffix.lower() != ".dll" or not path.is_file() or path.is_relative_to(Path(root).resolve()):
        return None
    return str(path)


def remembered_mola_path(root):
    try:
        return valid_mola_path(root, read_json(Path(root) / "output/local_settings.json").get("mola_dll_path"))
    except (OSError, ValueError, AttributeError):
        return None


def remember_mola_path(root, value):
    path = valid_mola_path(root, value)
    if path is None:
        raise ValueError("Provide an existing standalone DLL outside CHESHIRE; no search or copy.")
    settings = Path(root) / "output/local_settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(settings, {"mola_dll_path": path})
    return path
