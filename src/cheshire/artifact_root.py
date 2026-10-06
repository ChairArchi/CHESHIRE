"""Explicit portable study artifact paths; existing project defaults are intact."""
from dataclasses import dataclass
from pathlib import Path,PureWindowsPath


@dataclass(frozen=True)
class ArtifactRoot:
    path:Path
    def __post_init__(self): object.__setattr__(self,'path',Path(self.path).resolve())
    def resolve(self,relative):
        text=str(relative); candidate=Path(text)
        if candidate.is_absolute() or PureWindowsPath(text).drive or '..' in candidate.parts or '..' in PureWindowsPath(text).parts:
            raise ValueError('Artifact identifiers must be relative and remain inside the configured root.')
        target=(self.path/candidate).resolve()
        if not target.is_relative_to(self.path): raise ValueError('Artifact path escapes the configured root.')
        return target
    def reference(self,path):
        path=Path(path).resolve()
        if not path.is_relative_to(self.path): raise ValueError('Artifact is outside the configured root.')
        return path.relative_to(self.path).as_posix()
