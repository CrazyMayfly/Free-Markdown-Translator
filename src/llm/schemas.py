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
