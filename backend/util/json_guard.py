"""
JSON schema validator and auto-retry wrapper for LLM integration
Provides functions for extracting JSON from text, validating JSON against a schema, 
and building repair messages for invalid JSON.
"""

import json
import re
from typing import Any, Dict, Tuple, List

try:
    import jsonschema
    HAVE_JSONSCHEMA = True
except Exception:
    HAVE_JSONSCHEMA = False

JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)

def _extract_json(text: str) -> str:
    """Accepts raw LLM text. If fenced, extract; else assume whole string is JSON."""
    m = JSON_BLOCK.search(text or "")
    return m.group(1) if m else (text or "").strip()

def _min_validate(instance: Any, schema: Dict[str, Any]) -> List[str]:
    """Minimal structural validation when jsonschema isn't available."""
    errs = []
    if not isinstance(instance, dict):
        return ["Top-level output must be a JSON object."]
    req = schema.get("required", [])
    for k in req:
        if k not in instance:
            errs.append(f"Missing required field: {k}")
    props = schema.get("properties", {})
    for k, spec in props.items():
        if k in instance and "type" in spec:
            exp = spec["type"]
            val = instance[k]
            ok = (
                (exp == "object" and isinstance(val, dict)) or
                (exp == "array" and isinstance(val, list)) or
                (exp == "string" and isinstance(val, str)) or
                (exp == "number" and isinstance(val, (int, float))) or
                (exp == "boolean" and isinstance(val, bool))
            )
            if not ok:
                errs.append(f"Field `{k}` must be of type {exp}")
    return errs

def validate_json(instance: Any, schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    if HAVE_JSONSCHEMA:
        try:
            jsonschema.validate(instance=instance, schema=schema)
            return True, []
        except jsonschema.ValidationError as e:
            path = ".".join([str(p) for p in e.path]) or "(root)"
            return False, [f"{path}: {e.message}"]
        except Exception as e:
            return False, [f"Validator error: {e}"]
    return (lambda errs=_min_validate(instance, schema): (len(errs) == 0, errs))()

def parse_and_validate(raw_text: str, schema: Dict[str, Any]) -> Tuple[bool, Any, List[str]]:
    text = _extract_json(raw_text)
    try:
        data = json.loads(text)
    except Exception as e:
        return False, None, [f"Invalid JSON: {e}"]
    ok, errors = validate_json(data, schema)
    return ok, data, errors

REPAIR_NOTE = (
    "Your previous output was invalid for this JSON schema. "
    "Return ONLY valid JSON (no prose, no code fences). Fix the following issues:"
)

def build_repair_message(errors: List[str], max_items: int = 5) -> str:
    bullet = "\n- " + "\n- ".join(errors[:max_items])
    overflow = "" if len(errors) <= max_items else f"\n- ... and {len(errors) - max_items} more"
    return REPAIR_NOTE + bullet + overflow