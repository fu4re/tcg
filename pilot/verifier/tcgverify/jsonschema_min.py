"""Minimal JSON Schema 2020-12 validator for the keywords our schemas use.

Fails closed: a schema keyword outside SUPPORTED raises SchemaError instead of
being ignored, so a schema edit can never silently weaken validation.
Stdlib only (no `jsonschema` dependency, per the pilot rules).
"""
from __future__ import annotations

import re

SUPPORTED = {
    "$schema", "$id", "$defs", "$ref", "title", "description", "type", "const",
    "enum", "pattern", "minLength", "minimum", "required", "properties",
    "additionalProperties", "items", "minItems", "maxItems", "contains",
    "minContains", "maxContains", "allOf", "anyOf", "if", "then", "else",
}
_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


class SchemaError(Exception):
    pass


def _eq(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


def validate(instance, schema: dict) -> list[str]:
    """Return a list of error strings; [] means valid."""
    errors: list[str] = []
    _check(instance, schema, schema, "$", errors)
    return errors


def _check(inst, sch, root, where, errs) -> None:
    if sch is True:
        return
    if sch is False:
        errs.append(f"{where}: no value allowed")
        return
    unknown = set(sch) - SUPPORTED
    if unknown:
        raise SchemaError(f"unsupported schema keyword(s) {sorted(unknown)} at {where}")
    if "$ref" in sch:
        ref = sch["$ref"]
        if not ref.startswith("#/$defs/"):
            raise SchemaError(f"only local $defs refs are supported: {ref}")
        _check(inst, root["$defs"][ref[len("#/$defs/"):]], root, where, errs)
    if "type" in sch:
        types = sch["type"] if isinstance(sch["type"], list) else [sch["type"]]
        if not any(_TYPES[t](inst) for t in types):
            errs.append(f"{where}: expected type {sch['type']}")
            return
    if "const" in sch and not _eq(inst, sch["const"]):
        errs.append(f"{where}: must equal {sch['const']!r}")
    if "enum" in sch and not any(_eq(inst, e) for e in sch["enum"]):
        errs.append(f"{where}: must be one of {sch['enum']!r}")
    if isinstance(inst, str):
        if "pattern" in sch and not re.search(sch["pattern"], inst):
            errs.append(f"{where}: does not match {sch['pattern']!r}")
        if len(inst) < sch.get("minLength", 0):
            errs.append(f"{where}: shorter than {sch['minLength']}")
    if "minimum" in sch and _TYPES["integer"](inst) and inst < sch["minimum"]:
        errs.append(f"{where}: below minimum {sch['minimum']}")
    if isinstance(inst, dict):
        for k in sch.get("required", []):
            if k not in inst:
                errs.append(f"{where}: missing required {k!r}")
        props = sch.get("properties", {})
        for k, v in inst.items():
            if k in props:
                _check(v, props[k], root, f"{where}.{k}", errs)
            elif "additionalProperties" in sch:
                _check(v, sch["additionalProperties"], root, f"{where}.{k}", errs)
    if isinstance(inst, list):
        if len(inst) < sch.get("minItems", 0):
            errs.append(f"{where}: fewer than {sch['minItems']} items")
        if "maxItems" in sch and len(inst) > sch["maxItems"]:
            errs.append(f"{where}: more than {sch['maxItems']} items")
        if "items" in sch:
            for i, v in enumerate(inst):
                _check(v, sch["items"], root, f"{where}[{i}]", errs)
        if "contains" in sch:
            n = sum(1 for v in inst if _ok(v, sch["contains"], root))
            lo, hi = sch.get("minContains", 1), sch.get("maxContains")
            if n < lo or (hi is not None and n > hi):
                errs.append(f"{where}: {n} item(s) match 'contains', need "
                            f"{lo}..{hi if hi is not None else 'inf'}")
    for sub in sch.get("allOf", []):
        _check(inst, sub, root, where, errs)
    if "anyOf" in sch and not any(_ok(inst, s, root) for s in sch["anyOf"]):
        errs.append(f"{where}: matches none of anyOf")
    if "if" in sch:
        branch = sch.get("then") if _ok(inst, sch["if"], root) else sch.get("else")
        if branch is not None:
            _check(inst, branch, root, where, errs)


def _ok(inst, sch, root) -> bool:
    e: list[str] = []
    _check(inst, sch, root, "$", e)
    return not e
