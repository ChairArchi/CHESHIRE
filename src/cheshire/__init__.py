"""CHESHIRE mesh infrastructure, measurement, and scalar field mapping."""

from .attributes import analyze_vertex_attributes, attribute_summary
from .mapping import build_scalar_field, inverse, linear, map_attribute, power, sine, smoothstep
from .mesh_io import load_mesh, save_mesh
from .normalization import normalize_values
from .validation import inspect_mesh, validate_mesh

__all__ = [
    "load_mesh", "save_mesh", "inspect_mesh", "validate_mesh",
    "analyze_vertex_attributes", "attribute_summary", "normalize_values",
    "linear", "inverse", "smoothstep", "power", "sine",
    "map_attribute", "build_scalar_field",
]
