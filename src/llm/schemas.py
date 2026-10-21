"""JSON Schemas for OpenAI-style Structured Outputs (strict mode).

Strict mode requires: every object declares additionalProperties=false and
lists every property in required. These schemas are passed to the provider
via chat_json(response_schema=...) so the model's output shape is guaranteed
by constrained decoding instead of retry loops.
"""

TRANSLATION_SCHEMA_NAME = "mdtx_translation_response"

TRANSLATION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "segment_id": {"type": "string"},
                    "translated_text": {"type": "string"},
                    "notes": {"type": "array", "items": {"type": "string"}},
                    "applied_terms": {"type": "object", "additionalProperties": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
                "required": ["segment_id", "translated_text", "notes", "applied_terms", "confidence"],
                "additionalProperties": False,
            },
        },
        "context_requests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "segment_id": {"type": "string"},
                    "need": {"type": "string", "enum": ["similar_translations", "neighbour_translations"]},
                    "reason": {"type": "string"},
                },
                "required": ["segment_id", "need", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["translations", "context_requests"],
    "additionalProperties": False,
}

REFLECTION_SCHEMA_NAME = "mdtx_reflection_response"

# Compact translation schemas. The full schema above remains for improve /
# guard / harmonize callers; translate uses one of these depending on mode.
TRANSLATION_FAST_SCHEMA = {
    "type": "object",
    "properties": {
        "t": {
            "type": "array",
            "items": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 2,
            },
        }
    },
    "required": ["t"],
    "additionalProperties": False,
}

TRANSLATION_COMPACT_SCHEMA = {
    "type": "object",
    "properties": {
        "t": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "string"},
                    "x": {"type": "string"},
                    "c": {"type": "number"},
                },
                "required": ["i", "x", "c"],
                "additionalProperties": False,
            },
        },
        "q": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "string"},
                    "need": {"type": "string", "enum": ["similar_translations", "neighbour_translations"]},
                    "why": {"type": "string"},
                },
                "required": ["i", "need", "why"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["t", "q"],
    "additionalProperties": False,
}

TRANSLATION_QUALITY_SCHEMA = {
    "type": "object",
    "properties": {
        "t": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "string"},
                    "x": {"type": "string"},
                    "c": {"type": "number"},
                    "a": {"type": "object", "additionalProperties": {"type": "string"}},
                    "n": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["i", "x", "c", "a", "n"],
                "additionalProperties": False,
            },
        },
        "q": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "string"},
                    "need": {"type": "string", "enum": ["similar_translations", "neighbour_translations"]},
                    "why": {"type": "string"},
                },
                "required": ["i", "need", "why"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["t", "q"],
    "additionalProperties": False,
}


BRIEF_FAST_SCHEMA = {
    "type": "object",
    "properties": {
        "tone": {"type": "string"},
        "aud": {"type": "string"},
        "g": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "rendering": {"type": "string"},
                },
                "required": ["term", "rendering"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["tone", "aud", "g"],
    "additionalProperties": False,
}

BRIEF_SCHEMA_NAME = "mdtx_document_brief"

BRIEF_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "s": {"type": "string"},
        "tone": {"type": "string"},
        "aud": {"type": "string"},
        "g": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "rendering": {"type": "string"},
                },
                "required": ["term", "rendering"],
                "additionalProperties": False,
            },
        },
        "sec": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "h": {"type": "string"},
                    "sum": {"type": "string"},
                },
                "required": ["h", "sum"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["s", "tone", "aud", "g", "sec"],
    "additionalProperties": False,
}

GLOSSARY_SCHEMA_NAME = "mdtx_glossary_response"

GLOSSARY_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "terms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "rendering": {"type": "string"},
                },
                "required": ["term", "rendering"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["terms"],
    "additionalProperties": False,
}

REFLECTION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "segment_id": {"type": "string"},
                    "type": {"type": "string", "enum": ["accuracy", "fluency", "terminology", "style", "format"]},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "comment": {"type": "string"},
                },
                "required": ["segment_id", "type", "severity", "comment"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["issues"],
    "additionalProperties": False,
}

JUDGE_SCHEMA_NAME = "mdtx_judge_response"

JUDGE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "object",
            "properties": {
                "accuracy": {"type": "number"},
                "fluency": {"type": "number"},
                "terminology": {"type": "number"},
                "format": {"type": "number"},
            },
            "required": ["accuracy", "fluency", "terminology", "format"],
            "additionalProperties": False,
        },
        "overall": {"type": "number"},
        "comments": {"type": "array", "items": {"type": "string"}},
        "weak_segments": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["scores", "overall", "comments", "weak_segments"],
    "additionalProperties": False,
}
