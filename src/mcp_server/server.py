"""MCP server exposing mdtx translation as agent-callable tools.

Run with `mdtx --serve` (stdio transport). Requires the optional extra:
    pip install "mdtx[mcp]"

Tools:
- translate_markdown(path, target_langs, ...): translate a Markdown file,
  reusing the full pipeline (structured outputs, reflection review, format
  guard, translation memory) and returning per-language results.
- evaluate_translation(path, target_lang): translate and score with the
  LLM-as-judge.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from src.cli.commands import _build_provider, build_pipeline
from src.infra.config import TranslatorConfig, load_config
from src.memory.translation_memory import build_memory

try:
    from mcp.server.mcpserver import Context, MCPServer
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
    raise SystemExit(
        "The mcp SDK is required for mdtx --serve. Install it with: pip install 'mdtx[mcp]' (or pip install mcp)"
    ) from exc

server = MCPServer("mdtx")


def _prepare_config(mode: str | None, tone: str | None, model: str | None) -> TranslatorConfig:
    config = load_config()
    if mode:
        config.pipeline.mode = mode
    if tone:
        config.style.tone = tone
    if model:
        config.provider.model = model
    return config


def _progress_reporter(ctx: Context | None, total: int):
    """Bridge sync bundle_progress_callback into async ctx.report_progress."""
    state = {"done": 0, "total": total}

    def callback(input_path: Path, target_lang: str, bundle_id: str) -> None:
        state["done"] += 1
        if ctx is None:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(ctx.report_progress(state["done"], state["total"]))
        except RuntimeError:  # no running loop; progress is best-effort
            pass

    return callback


@server.tool()
async def translate_markdown(
    path: str,
    target_langs: list[str],
    mode: str | None = None,
    tone: str | None = None,
    model: str | None = None,
    write: bool = True,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Translate a Markdown document to one or more target languages.

    The AST-based pipeline preserves markdown structure, code blocks, links
    and placeholders; optional review and format-repair agents run per mode.

    Args:
        path: Markdown file to translate (absolute or workspace-relative).
        target_langs: Target language names or codes, e.g. ["chinese", "ja"].
        mode: Pipeline mode "fast" | "balanced" | "strict" (default: config).
        tone: Style tone override, e.g. "technical".
        model: Model name override.
        write: Also write the translated .md file next to the source.

    Returns:
        Per-language results with output_path, validation status, token usage
        and the translated markdown text.
    """
    config = _prepare_config(mode, tone, model)
    input_path = Path(path).expanduser()
    if not input_path.is_file():
        raise FileNotFoundError(f"Markdown file not found: {input_path}")

    memory = build_memory(config)
    pipeline = build_pipeline(config, memory=memory)
    semaphore = asyncio.Semaphore(max(1, config.execution.max_parallel_translations))
    results: dict[str, Any] = {}
    for target_lang in target_langs:
        progress = _progress_reporter(ctx, total=pipeline.count_bundles(input_path, target_lang))
        result = await pipeline.run_async(
            input_path,
            target_lang,
            write_output=write,
            semaphore=semaphore,
            bundle_progress_callback=progress,
        )
        results[target_lang] = {
            "output_path": str(result.output_path) if result.output_path else None,
            "validation_passed": result.validation.passed,
            "validation_errors": result.validation.errors,
            "segments": len(result.segments),
            "token_usage": {
                "prompt": result.api_usage.total.prompt_tokens,
                "completion": result.api_usage.total.completion_tokens,
                "cached": result.api_usage.total.cached_tokens,
            },
            "translated_markdown": result.translated_text,
        }
    return results


@server.tool()
async def evaluate_translation(
    path: str,
    target_lang: str,
    model: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Translate a Markdown document and score it with the LLM-as-judge.

    Returns accuracy / fluency / terminology / format scores (1-5), an
    overall score and reviewer comments. Nothing is written to disk.
    """
    from src.agents.judge_agent import JudgeAgent

    config = _prepare_config(None, None, model)
    input_path = Path(path).expanduser()
    if not input_path.is_file():
        raise FileNotFoundError(f"Markdown file not found: {input_path}")

    pipeline = build_pipeline(config, memory=build_memory(config))
    result = await pipeline.run_async(input_path, target_lang, write_output=False)
    judge = JudgeAgent(_build_provider(config))
    judge_report = await judge.evaluate_async(result.segments, result.translations, result.context, target_lang)
    judge_report["input_path"] = str(input_path)
    judge_report["validation_passed"] = result.validation.passed
    return judge_report


def serve() -> None:
    logging.getLogger().setLevel(logging.WARNING)  # keep stdio clean for MCP
    server.run(transport="stdio")
