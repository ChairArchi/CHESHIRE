"""CHESHIRE mesh fields, rule selection, budgeting, and normal displacement."""

from .attributes import analyze_vertex_attributes, attribute_summary
from .execution import ExecutionBudget, plan_execution
from .mapping import build_scalar_field, inverse, linear, map_attribute, power, sine, smoothstep
from .mesh_io import load_mesh, save_mesh
from .normalization import normalize_values
from .rules import Rule, evaluate_face_rule, evaluate_vertex_rule
from .transforms import TransformResult, displace_vertices_along_normals
from .validation import inspect_mesh, validate_mesh

__all__ = [
    "load_mesh", "save_mesh", "inspect_mesh", "validate_mesh",
    "analyze_vertex_attributes", "attribute_summary", "normalize_values",
    "linear", "inverse", "smoothstep", "power", "sine",
    "map_attribute", "build_scalar_field",
    "Rule", "evaluate_vertex_rule", "evaluate_face_rule",
    "ExecutionBudget", "plan_execution",
    "TransformResult", "displace_vertices_along_normals",
]
