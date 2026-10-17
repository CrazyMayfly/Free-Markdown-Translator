from __future__ import annotations

import contextlib
import contextvars
import logging

from colorlog import ColoredFormatter

_log_context: contextvars.ContextVar[str] = contextvars.ContextVar("log_context", default="")
_RESET = "\033[0m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_BOLD_RED = "\033[1;31m"


class _SuppressHttpRequestLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        return not (isinstance(message, str) and message.startswith("HTTP Request:"))


class _TaskContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.task_context = _log_context.get("")
        return True


class _MessageColorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "success_log", False):
            record.message_log_color = _GREEN
        elif record.levelno >= logging.CRITICAL:
            record.message_log_color = _BOLD_RED
        elif record.levelno >= logging.ERROR:
            record.message_log_color = _RED
        elif record.levelno >= logging.WARNING:
            record.message_log_color = _YELLOW
        else:
            record.message_log_color = ""
        return True


@contextlib.contextmanager
def log_task_context(label: str):
    token = _log_context.set(f"[{label}] " if label else "")
    try:
        yield
    finally:
        _log_context.reset(token)


def log_success(message: str, *args, **kwargs) -> None:
    extra = dict(kwargs.pop("extra", {}) or {})
    extra["success_log"] = True
    logging.getLogger().info(message, *args, extra=extra, stacklevel=2, **kwargs)


_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    global _configured
    root_logger = logging.getLogger()
    if _configured:
        root_logger.setLevel(level)
        return

    formatter = ColoredFormatter(
        "%(blue)s%(asctime)s %(log_color)s[%(levelname)-7s]%(reset)s %(blue)s%(task_context)s%(reset)s%(message_log_color)s%(message)s%(reset)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "white",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(_SuppressHttpRequestLogFilter())
    handler.addFilter(_TaskContextFilter())
    handler.addFilter(_MessageColorFilter())
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    for logger_name in ("openai", "openai._base_client", "httpx", "httpcore"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    _configured = True
