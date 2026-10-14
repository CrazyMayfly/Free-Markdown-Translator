from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.core.types import ApiUsageSummary


class LLMProvider(ABC):
    @abstractmethod
    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        call_label: str = "llm",
        response_schema: dict | None = None,
    ) -> Any:
        """Send a single-turn chat request and return parsed JSON.

        When response_schema is provided, providers that support Structured
        Outputs should pass it through so the response shape is enforced by
        constrained decoding; callers must still tolerate plain-JSON responses.
        """
        raise NotImplementedError

    @abstractmethod
    def get_usage_summary(self) -> ApiUsageSummary:
        raise NotImplementedError
