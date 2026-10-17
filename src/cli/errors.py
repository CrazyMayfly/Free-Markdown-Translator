from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import yaml

from src.infra.config import default_user_config_path


@dataclass(frozen=True)
class CliErrorPresentation:
    message: str
    exit_code: int = 1


def _extract_model_service_error_message(exc: Exception) -> str | None:
    body = getattr(exc, "body", None)
    if isinstance(body, str):
        message = body.strip()
        return message or None
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            candidate = error.get("message")
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        candidate = body.get("message")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    response = getattr(exc, "response", None)
    if response is not None:
        data: Any = None
        try:
            json_method = getattr(response, "json", None)
            if callable(json_method):
                data = json_method()
        except Exception:
            data = None
        if isinstance(data, dict):
            error = data.get("error")
            if isinstance(error, dict):
                candidate = error.get("message")
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            candidate = data.get("message")
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

    message = str(exc).strip()
    return message or None


def present_cli_error(exc: Exception, *, verbose: bool) -> CliErrorPresentation:
    if verbose:
        logging.exception("Command failed.")
    else:
        logging.debug("Command failed with suppressed traceback.", exc_info=exc)

    if isinstance(exc, FileNotFoundError):
        return CliErrorPresentation(
            "\n".join(
                [
                    "Input file or directory was not found.",
                    f"Path: {exc}",
                    "Please check the path and try again.",
                ]
            )
        )

    if isinstance(exc, yaml.YAMLError):
        return CliErrorPresentation(
            "\n".join(
                [
                    "Config file could not be parsed.",
                    "Please check the YAML syntax in your config file and try again.",
                ]
            )
        )

    if isinstance(exc, ModuleNotFoundError) and exc.name == "openai":
        return CliErrorPresentation(
            "\n".join(
                [
                    "The OpenAI dependency is not installed.",
                    "Install dependencies first, then run the command again.",
                ]
            )
        )

    if isinstance(exc, ValueError):
        message = str(exc)
        if "No API key available" in message:
            config_path = default_user_config_path()
            return CliErrorPresentation(
                "\n".join(
                    [
                        "OpenAI API key is missing.",
                        f"Set `provider.api_key` in `{config_path}` or set the environment variable named by `provider.api_key_env`.",
                    ]
                )
            )
        if message.startswith("No input files matched pattern:"):
            pattern = message.split(":", 1)[1].strip()
            return CliErrorPresentation(
                "\n".join(
                    [
                        "No Markdown files matched the current input rule.",
                        f"Pattern: {pattern}",
                        "Please check `--match` or your `input.file_pattern` config.",
                    ]
                )
            )
        if message.startswith("`--to` expects language codes"):
            return CliErrorPresentation(message)
        if message.startswith("Provider ") and " is not implemented." in message:
            return CliErrorPresentation(
                "\n".join(
                    [
                        "The configured provider is not supported by this build.",
                        message,
                    ]
                )
            )

    # The guard below short-circuits before the class names are evaluated,
    # so this module stays importable without the openai extra installed.
    try:
        from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError

        api_error_types: tuple[type[Exception], ...] = (
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            AuthenticationError,
            RateLimitError,
        )
    except ModuleNotFoundError:
        api_error_types = ()

    if api_error_types and isinstance(exc, APIConnectionError):
        return CliErrorPresentation(
            "\n".join(
                [
                    "Could not connect to the model service.",
                    "Please check your network, proxy, or `provider.base_url` setting and try again.",
                ]
            )
        )

    if api_error_types and isinstance(exc, APITimeoutError):
        return CliErrorPresentation(
            "\n".join(
                [
                    "The model service timed out.",
                    "Please try again in a moment, or reduce concurrency / bundle size.",
                ]
            )
        )

    if api_error_types and isinstance(exc, AuthenticationError):
        return CliErrorPresentation(
            "\n".join(
                [
                    "Authentication with the model service failed.",
                    "Please verify your API key and `provider.base_url` configuration.",
                ]
            )
        )

    if api_error_types and isinstance(exc, RateLimitError):
        return CliErrorPresentation(
            "\n".join(
                [
                    "The model service rate limit was reached.",
                    "Please wait a moment and retry, or lower `execution.max_parallel_translations`.",
                ]
            )
        )

    if api_error_types and isinstance(exc, APIStatusError):
        status_code = getattr(exc, "status_code", "unknown")
        provider_message = _extract_model_service_error_message(exc)
        if provider_message:
            logging.error("Model service error details (HTTP %s): %s", status_code, provider_message)
        else:
            logging.error("Model service error details unavailable (HTTP %s).", status_code)
        return CliErrorPresentation(
            "\n".join(
                [
                    f"The model service returned an error (HTTP {status_code}).",
                    "Please retry later or check your provider configuration.",
                ]
            )
        )

    return CliErrorPresentation(
        "\n".join(
            [
                "Translation failed due to an unexpected error.",
                "Run with `--verbose` to see the full traceback.",
            ]
        )
    )
