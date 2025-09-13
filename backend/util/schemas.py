"""
JSON Schemas for Summarizer and Planner LLM outputs
"""

SUMMARIZER_SCHEMA = {
    "type": "object",
    "required": ["concept_alias_map_updated", "dominance_by_item", "concept_readiness_labels", "pair_coverage_labels"],
    "properties": {
        "concept_alias_map_updated": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["semantic_id", "canonical_label", "members"],
                "properties": {
                    "semantic_id": {"type": "string"},
                    "canonical_label": {"type": "string"},
                    "members": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "dominance_by_item": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["dominant"],
                "properties": {
                    "dominant": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
                    "secondary": {"type": "array", "items": {"type": "string"}},
                    "dominance_confidence": {"type": "string", "enum": ["low", "med", "high"]}
                }
            }
        },
        "concept_readiness_labels": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["semantic_id", "pair", "reason_codes"],
                "properties": {
                    "semantic_id": {"type": "string"},
                    "pair": {"type": "string"},
                    "reason_codes": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["skipped", "forever_wrong", "wrong_1_to_3", "wrong_gt_3", "cold_start"]},
                        "minItems": 1
                    }
                }
            }
        },
        "pair_coverage_labels": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["pair", "coverage_debt"],
                "properties": {
                    "pair": {"type": "string"},
                    "coverage_debt": {"type": "string", "enum": ["low", "med", "high"]}
                }
            }
        },
        "notes": {"type": "string"}
    }
}

PLANNER_SCHEMA = {
    "type": "object",
    "required": ["pack", "constraint_report"],
    "properties": {
        "pack": {
            "type": "array",
            "minItems": 12,
            "maxItems": 12,
            "items": {
                "type": "object",
                "required": ["item_id", "bucket", "why"],
                "properties": {
                    "item_id": {"type": "string"},
                    "bucket": {"type": "string", "enum": ["Easy", "Medium", "Hard"]},
                    "why": {
                        "type": "object",
                        "required": ["semantic_concepts", "pair", "pyq_frequency_score"],
                        "properties": {
                            "semantic_concepts": {"type": "array", "items": {"type": "string"}},
                            "readiness": {"type": "string", "enum": ["Weak", "Moderate", "Strong"]},
                            "pair": {"type": "string"},
                            "pyq_frequency_score": {"type": "number", "enum": [0.5, 1.0, 1.5]}
                        }
                    }
                }
            }
        },
        "constraint_report": {
            "type": "object",
            "required": ["met", "relaxed"],
            "properties": {
                "met": {"type": "array", "items": {"type": "string"}},
                "relaxed": {"type": "array", "items": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {"name": {"type": "string"}, "reason": {"type": "string"}}
                }},
                "meta": {
                    "type": "object",
                    "properties": {
                        "pool_expanded": {"type": "boolean"},
                        "retry_used": {"type": "boolean"}
                    }
                }
            }
        },
        "session_notes": {"type": "string"}
    }
}