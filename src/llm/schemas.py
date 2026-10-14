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
        }
    },
    "required": ["translations"],
    "additionalProperties": False,
}

REFLECTION_SCHEMA_NAME = "mdtx_reflection_response"

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
    },
    "required": ["scores", "overall", "comments"],
    "additionalProperties": False,
}
