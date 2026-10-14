from __future__ import annotations

import json
import logging
import os
import threading
import time

from src.core.types import ApiUsageSummary
from src.llm.provider import LLMProvider


class OpenAIProvider(LLMProvider):
    # structured_outputs: "auto" tries json_schema and permanently falls back to
    # json_object on the first rejection (Ollama/vLLM-style endpoints may not
    # implement it); "on" always uses json_schema; "off" always uses json_object.
    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        api_key_env: str,
        model: str,
        temperature: float,
        max_tokens: int,
        structured_outputs: str = "auto",
    ) -> None:
        from openai import OpenAI

        resolved_api_key = self._resolve_api_key(api_key=api_key, api_key_env=api_key_env)
        self.client = OpenAI(api_key=resolved_api_key or "mdtx-no-auth", base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.structured_outputs_mode = (structured_outputs or "auto").strip().lower()
        if self.structured_outputs_mode not in {"auto", "on", "off"}:
            logging.warning("Invalid provider.structured_outputs=%s; falling back to auto", structured_outputs)
            self.structured_outputs_mode = "auto"
        self._structured_supported: bool | None = None  # None = not probed yet
        self._usage_lock = threading.Lock()
        self._usage_summary = ApiUsageSummary()

    def chat_json(self, system_prompt: str, user_prompt: str, call_label: str = "llm", response_schema: dict | None = None):
        start = time.perf_counter()
        logging.info(
            "LLM start: %s model=%s chars=%s/%s",
            call_label,
            self.model,
            len(system_prompt),
            len(user_prompt),
        )
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug("Model input [system] (%s):\n%s", call_label, system_prompt)
            logging.debug("Model input [user] (%s):\n%s", call_label, user_prompt)

        response_format, using_structured = self._resolve_response_format(call_label, response_schema)
        try:
            response = self._create_completion(system_prompt, user_prompt, response_format)
        except Exception as exc:
            if not (using_structured and self._should_fallback(exc)):
                raise
            with self._usage_lock:
                already_degraded = self._structured_supported is False
                self._structured_supported = False
            if already_degraded:
                raise
            logging.warning(
                "Endpoint rejected structured outputs (json_schema) for %s; permanently falling back to json_object. error=%s",
                call_label,
                exc,
            )
            response = self._create_completion(system_prompt, user_prompt, {"type": "json_object"})

        content = response.choices[0].message.content or "{}"
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens
        self._record_usage(
            call_label=call_label,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logging.info(
            "LLM done: %s %sms chars=%s tokens=%s/%s/%s",
            call_label,
            elapsed_ms,
            len(content),
            prompt_tokens,
            completion_tokens,
            total_tokens,
        )
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug("Model output [raw] (%s):\n%s", call_label, content)
        return json.loads(content)

    def get_usage_summary(self) -> ApiUsageSummary:
        with self._usage_lock:
            summary = ApiUsageSummary()
            summary.merge(self._usage_summary)
            return summary

    def _resolve_response_format(self, call_label: str, response_schema: dict | None) -> tuple[dict, bool]:
        """Returns (response_format, using_structured)."""
        if response_schema is None or self.structured_outputs_mode == "off":
            return {"type": "json_object"}, False
        if self.structured_outputs_mode == "auto" and self._structured_supported is False:
            return {"type": "json_object"}, False
        schema_name = f"mdtx_{call_label}_response"
        return (
            {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": response_schema,
                },
            },
            True,
        )

    def _should_fallback(self, exc: Exception) -> bool:
        # Only fall back when the endpoint itself rejected the json_schema
        # request (HTTP 400 / unsupported parameter), not on transient errors.
        if self.structured_outputs_mode != "auto":
            return False
        status_code = getattr(exc, "status_code", None)
        if status_code is not None:
            return int(status_code) == 400
        try:
            from openai import BadRequestError

            return isinstance(exc, BadRequestError)
        except ImportError:  # pragma: no cover - openai always ships this
            return False

    def _create_completion(self, system_prompt: str, user_prompt: str, response_format: dict):
        return self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format=response_format,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

    def _record_usage(self, call_label: str, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> None:
        with self._usage_lock:
            self._usage_summary.add(
                call_label=call_label,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

    @staticmethod
    def _resolve_api_key(api_key: str | None, api_key_env: str) -> str:
        if api_key:
            return api_key
        if not api_key_env:
            return ""
        if api_key_env.startswith(("sk-", "sess-", "Bearer ")) or len(api_key_env) > 24:
            return api_key_env
        return os.getenv(api_key_env, "")
