"""CHESHIRE mesh fields, transforms, and backend-independent inheritance."""

from .attributes import analyze_vertex_attributes, attribute_summary
from .execution import ExecutionBudget, check_execution_budget, plan_execution
from .inheritance import FieldSpec, InheritedFieldSet, inherit_fields
from .lineage import LineageMap, ParentRef, identity_lineage, validate_lineage
from .mapping import build_scalar_field, inverse, linear, map_attribute, power, sine, smoothstep
from .mesh_io import load_mesh, save_mesh
from .normalization import normalize_values
from .rules import Rule, evaluate_face_rule, evaluate_vertex_rule
from .subdivision import SubdivisionResult, estimate_quad_subdivision, subdivide_quad_once
from .transforms import TransformResult, displace_vertices_along_normals
from .validation import inspect_mesh, validate_lineage_coverage, validate_mesh

__all__ = [
    "load_mesh", "save_mesh", "inspect_mesh", "validate_mesh",
    "analyze_vertex_attributes", "attribute_summary", "normalize_values",
    "linear", "inverse", "smoothstep", "power", "sine",
    "map_attribute", "build_scalar_field",
    "Rule", "evaluate_vertex_rule", "evaluate_face_rule",
    "ExecutionBudget", "plan_execution",
    "TransformResult", "displace_vertices_along_normals",
    "ParentRef", "LineageMap", "validate_lineage", "identity_lineage",
    "FieldSpec", "InheritedFieldSet", "inherit_fields",
    "check_execution_budget", "validate_lineage_coverage",
    "SubdivisionResult", "estimate_quad_subdivision", "subdivide_quad_once",
]
