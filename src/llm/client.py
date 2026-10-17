from __future__ import annotations

import json
import logging
import os
import threading
import time

from openai import AsyncOpenAI, BadRequestError, OpenAI

from src.core.errors import LLMResponseTruncatedError
from src.core.types import ApiUsageSummary
from src.llm.provider import LLMProvider

_JSON_OBJECT_FORMAT = {"type": "json_object"}


def _resolve_api_key(api_key: str | None, api_key_env: str) -> str:
    if api_key:
        return api_key
    if not api_key_env:
        return ""
    if api_key_env.startswith(("sk-", "sess-", "Bearer ")) or len(api_key_env) > 24:
        return api_key_env
    return os.getenv(api_key_env, "")


def _normalize_structured_mode(structured_outputs: str | None) -> str:
    mode = (structured_outputs or "auto").strip().lower()
    if mode not in {"auto", "on", "off"}:
        logging.warning("Invalid provider.structured_outputs=%s; falling back to auto", structured_outputs)
        return "auto"
    return mode


def _resolve_response_format(call_label: str, response_schema: dict | None, mode: str, supported: bool | None) -> tuple[dict, bool]:
    """Returns (response_format, using_structured)."""
    if response_schema is None or mode == "off":
        return _JSON_OBJECT_FORMAT, False
    if mode == "auto" and supported is False:
        return _JSON_OBJECT_FORMAT, False
    return (
        {
            "type": "json_schema",
            "json_schema": {
                "name": f"mdtx_{call_label}_response",
                "strict": True,
                "schema": response_schema,
            },
        },
        True,
    )


def _is_schema_rejection(exc: Exception, mode: str) -> bool:
    # Only fall back when the endpoint itself rejected the json_schema
    # request (HTTP 400 / unsupported parameter), not on transient errors.
    if mode != "auto":
        return False
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        return int(status_code) == 400
    return isinstance(exc, BadRequestError)


def _log_call_start(call_label: str, model: str, system_prompt: str, user_prompt: str) -> None:
    logging.info("LLM start: %s model=%s chars=%s/%s", call_label, model, len(system_prompt), len(user_prompt))
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug("Model input [system] (%s):\n%s", call_label, system_prompt)
        logging.debug("Model input [user] (%s):\n%s", call_label, user_prompt)


def _log_call_done(call_label: str, elapsed_ms: int, content: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cached_tokens: int = 0) -> None:
    logging.info(
        "LLM done: %s %sms chars=%s tokens=%s/%s/%s cached=%s",
        call_label,
        elapsed_ms,
        len(content),
        prompt_tokens,
        completion_tokens,
        total_tokens,
        cached_tokens,
    )
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug("Model output [raw] (%s):\n%s", call_label, content)


def _check_truncation(response, call_label: str, max_tokens: int) -> None:
    finish_reason = None
    if getattr(response, "choices", None):
        finish_reason = getattr(response.choices[0], "finish_reason", None)
    if finish_reason == "length":
        raise LLMResponseTruncatedError(
            f"LLM response for '{call_label}' was truncated by max_tokens={max_tokens} "
            "before completing valid JSON; increase provider.max_tokens or reduce segmentation.max_bundle_chars"
        )


def _extract_usage(response) -> tuple[int, int, int, int]:
    usage = getattr(response, "usage", None)
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
    if total_tokens == 0:
        total_tokens = prompt_tokens + completion_tokens
    details = getattr(usage, "prompt_tokens_details", None)
    cached_tokens = int(getattr(details, "cached_tokens", 0) or 0)
    return prompt_tokens, completion_tokens, total_tokens, cached_tokens


class _ProviderCore:
    """State and helpers shared by the sync and async OpenAI providers."""

    def __init__(self, base_url: str, api_key: str | None, api_key_env: str, model: str, temperature: float, max_tokens: int, structured_outputs: str, max_retries: int) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.structured_outputs_mode = _normalize_structured_mode(structured_outputs)
        self.max_retries = max(0, int(max_retries))
        self._resolved_api_key = _resolve_api_key(api_key=api_key, api_key_env=api_key_env)
        self._base_url = base_url
        self._structured_supported: bool | None = None  # None = not probed yet
        self._usage_lock = threading.Lock()
        self._usage_summary = ApiUsageSummary()

    def build_client_kwargs(self) -> dict:
        return {
            "api_key": self._resolved_api_key or "mdtx-no-auth",
            "base_url": self._base_url,
            "max_retries": self.max_retries,
        }

    def response_format(self, call_label: str, response_schema: dict | None) -> tuple[dict, bool]:
        return _resolve_response_format(call_label, response_schema, self.structured_outputs_mode, self._structured_supported)

    def mark_structured_unsupported(self) -> None:
        self._structured_supported = False

    def should_fallback(self, exc: Exception) -> bool:
        return _is_schema_rejection(exc, self.structured_outputs_mode)

    def record_usage(self, call_label: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cached_tokens: int = 0) -> None:
        with self._usage_lock:
            self._usage_summary.add(
                call_label=call_label,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cached_tokens=cached_tokens,
            )

    def usage_snapshot(self) -> ApiUsageSummary:
        with self._usage_lock:
            summary = ApiUsageSummary()
            summary.merge(self._usage_summary)
            return summary

    @staticmethod
    def completion_kwargs(system_prompt: str, user_prompt: str, response_format: dict, model: str, temperature: float, max_tokens: int) -> dict:
        return {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": response_format,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }


class OpenAIProvider(LLMProvider):
    """Synchronous OpenAI-compatible provider.

    structured_outputs: "auto" tries json_schema and permanently falls back to
    json_object on the first rejection (Ollama/vLLM-style endpoints may not
    implement it); "on" always uses json_schema; "off" always uses json_object.
    max_retries is delegated to the SDK, which retries connection errors,
    429/5xx responses with exponential backoff and honors Retry-After.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        api_key_env: str,
        model: str,
        temperature: float,
        max_tokens: int,
        structured_outputs: str = "auto",
        max_retries: int = 3,
    ) -> None:
        self._core = _ProviderCore(base_url, api_key, api_key_env, model, temperature, max_tokens, structured_outputs, max_retries)
        self.client = OpenAI(**self._core.build_client_kwargs())

    @property
    def model(self) -> str:
        return self._core.model

    def chat_json(self, system_prompt: str, user_prompt: str, call_label: str = "llm", response_schema: dict | None = None):
        _log_call_start(call_label, self._core.model, system_prompt, user_prompt)
        start = time.perf_counter()
        response_format, using_structured = self._core.response_format(call_label, response_schema)
        try:
            response = self.client.chat.completions.create(
                **self._core.completion_kwargs(system_prompt, user_prompt, response_format, self._core.model, self._core.temperature, self._core.max_tokens)
            )
        except Exception as exc:
            if not (using_structured and self._should_fallback(exc)):
                raise
            if self._core._structured_supported is False:
                raise
            self._core.mark_structured_unsupported()
            logging.warning(
                "Endpoint rejected structured outputs (json_schema) for %s; permanently falling back to json_object. error=%s",
                call_label,
                exc,
            )
            response = self.client.chat.completions.create(
                **self._core.completion_kwargs(system_prompt, user_prompt, _JSON_OBJECT_FORMAT, self._core.model, self._core.temperature, self._core.max_tokens)
            )

        content = response.choices[0].message.content or "{}"
        _check_truncation(response, call_label, self._core.max_tokens)
        prompt_tokens, completion_tokens, total_tokens, cached_tokens = _extract_usage(response)
        self._core.record_usage(call_label, prompt_tokens, completion_tokens, total_tokens, cached_tokens)
        _log_call_done(call_label, int((time.perf_counter() - start) * 1000), content, prompt_tokens, completion_tokens, total_tokens, cached_tokens)
        return json.loads(content)

    def _should_fallback(self, exc: Exception) -> bool:
        return self._core.should_fallback(exc)

    def get_usage_summary(self) -> ApiUsageSummary:
        return self._core.usage_snapshot()


class AsyncOpenAIProvider(LLMProvider):
    """Native-async twin of OpenAIProvider for the asyncio pipeline."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        api_key_env: str,
        model: str,
        temperature: float,
        max_tokens: int,
        structured_outputs: str = "auto",
        max_retries: int = 3,
    ) -> None:
        self._core = _ProviderCore(base_url, api_key, api_key_env, model, temperature, max_tokens, structured_outputs, max_retries)
        self.client = AsyncOpenAI(**self._core.build_client_kwargs())

    @property
    def model(self) -> str:
        return self._core.model

    def chat_json(self, system_prompt: str, user_prompt: str, call_label: str = "llm", response_schema: dict | None = None):
        raise NotImplementedError("AsyncOpenAIProvider only supports chat_json_async; call it via pipeline.run()/run_async().")

    async def chat_json_async(self, system_prompt: str, user_prompt: str, call_label: str = "llm", response_schema: dict | None = None):
        _log_call_start(call_label, self._core.model, system_prompt, user_prompt)
        start = time.perf_counter()
        response_format, using_structured = self._core.response_format(call_label, response_schema)
        try:
            response = await self.client.chat.completions.create(
                **self._core.completion_kwargs(system_prompt, user_prompt, response_format, self._core.model, self._core.temperature, self._core.max_tokens)
            )
        except Exception as exc:
            if not (using_structured and self._core.should_fallback(exc)):
                raise
            if self._core._structured_supported is False:
                raise
            self._core.mark_structured_unsupported()
            logging.warning(
                "Endpoint rejected structured outputs (json_schema) for %s; permanently falling back to json_object. error=%s",
                call_label,
                exc,
            )
            response = await self.client.chat.completions.create(
                **self._core.completion_kwargs(system_prompt, user_prompt, _JSON_OBJECT_FORMAT, self._core.model, self._core.temperature, self._core.max_tokens)
            )

        content = response.choices[0].message.content or "{}"
        _check_truncation(response, call_label, self._core.max_tokens)
        prompt_tokens, completion_tokens, total_tokens, cached_tokens = _extract_usage(response)
        self._core.record_usage(call_label, prompt_tokens, completion_tokens, total_tokens, cached_tokens)
        _log_call_done(call_label, int((time.perf_counter() - start) * 1000), content, prompt_tokens, completion_tokens, total_tokens, cached_tokens)
        return json.loads(content)

    def get_usage_summary(self) -> ApiUsageSummary:
        return self._core.usage_snapshot()
