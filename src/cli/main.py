from __future__ import annotations

import argparse
import copy
import logging
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.cli.commands import evaluate_command, translate_command
from src.cli.errors import present_cli_error
from src.infra.config import TranslatorConfig, initialize_config, load_config, resolve_config_path
from src.infra.logging import configure_logging


def _parse_bool_arg(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def _parse_positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("Value must be a positive integer.")
    return parsed


def _parse_target_languages(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    languages: list[str] = []
    for value in values:
        parts = [item.strip() for item in value.split(",")]
        languages.extend(item for item in parts if item)
    return languages or None


def _apply_cli_overrides(args: argparse.Namespace, config: TranslatorConfig) -> TranslatorConfig:
    resolved = copy.deepcopy(config)
    target_languages = _parse_target_languages(args.to)
    if target_languages is not None:
        resolved.target_languages = target_languages
    if args.output is not None:
        resolved.output.directory = args.output
    if args.mode is not None:
        resolved.pipeline.mode = args.mode
    if args.threads is not None:
        resolved.execution.max_parallel_translations = args.threads
    if args.match is not None:
        resolved.input.file_pattern = args.match
    if args.review is not None:
        resolved.pipeline.enable_review = args.review
    if args.guard is not None:
        resolved.pipeline.enable_format_guard = args.guard
    if args.tone is not None:
        resolved.style.tone = args.tone
    if args.model is not None:
        resolved.provider.model = args.model
    return resolved


def _provider_auth_source(config: TranslatorConfig) -> str:
    if config.provider.api_key:
        return "config.api_key"
    if os.getenv(config.provider.api_key_env):
        return f"env:{config.provider.api_key_env}"
    return f"not_set ({config.provider.api_key_env})"


def _log_startup_config(args: argparse.Namespace, config: TranslatorConfig) -> None:
    config_path = resolve_config_path(args.config)
    input_paths = [str(Path(path).resolve()) for path in args.paths]
    output_dir = str(Path(config.output.directory).resolve())
    logging.info(
        "Runtime: config=%s verbose=%s inputs=%s output=%s",
        str(config_path.resolve()) if config_path is not None else "<defaults>",
        args.verbose,
        input_paths,
        output_dir,
    )
    logging.info(
        "Translate: targets=%s tone=%s audience=%s terms=%s instructions=%s",
        config.target_languages,
        config.style.tone,
        config.style.audience,
        len(config.style.preserve_terms),
        len(config.style.instructions),
    )
    logging.info(
        "Provider: %s model=%s auth=%s temp=%s max_tokens=%s",
        config.provider.name,
        config.provider.model,
        _provider_auth_source(config),
        config.provider.temperature,
        config.provider.max_tokens,
    )
    logging.info(
        "Pipeline: mode=%s review=%s guard=%s fail_on_error=%s pattern=%s parallel=%s bundle=%s/%s report=%s",
        config.pipeline.mode,
        config.pipeline.enable_review,
        config.pipeline.enable_format_guard,
        config.pipeline.fail_on_validation_error,
        config.input.file_pattern,
        config.execution.max_parallel_translations,
        config.segmentation.max_bundle_chars,
        config.segmentation.max_bundle_segments,
        config.output.write_report,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mdtx", description="Agent-based Markdown translation pipeline.")
    parser.add_argument("--config", help="Path to config.yaml", default=None)
    parser.add_argument("--init-config", action="store_true", help="Create the default config file and exit. Defaults to ~/.mdtx/config.yaml.")
    parser.add_argument("--force-init-config", action="store_true", help="Overwrite an existing config file when used with --init-config.")
    parser.add_argument("--verbose", action="store_true", help="Enable more detailed logs.")
    parser.add_argument("paths", nargs="*", help="Markdown files or directories to translate.")
    parser.add_argument("--to", "-to", action="append", help="Target language(s), supports comma-separated values. Defaults to config.yaml.")
    parser.add_argument("-o", "--output", help="Output directory. Defaults to config.yaml output.directory.")
    parser.add_argument("-m", "--mode", help="Pipeline mode. Defaults to config.yaml pipeline.mode.")
    parser.add_argument("-t", "--threads", type=_parse_positive_int, help="Max parallel translations. Defaults to config.yaml execution.max_parallel_translations.")
    parser.add_argument("--match", help="Glob pattern for files under input directories. Defaults to config.yaml input.file_pattern.")
    parser.add_argument("--review", nargs="?", const=True, default=None, type=_parse_bool_arg, help="Enable or disable review agent. Defaults to config.yaml pipeline.enable_review.")
    parser.add_argument("--guard", nargs="?", const=True, default=None, type=_parse_bool_arg, help="Enable or disable format guard. Defaults to config.yaml pipeline.enable_format_guard.")
    parser.add_argument("--tone", help="Translation tone. Defaults to config.yaml style.tone.")
    parser.add_argument("--model", help="Model name. Defaults to config.yaml provider.model.")
    parser.add_argument("--eval", action="store_true", help="Translate without writing output, then run LLM-as-judge quality evaluation and print the judge report.")
    parser.add_argument("--resume", action="store_true", help="Resume an interrupted job: bundles already translated in a previous run are reused from the checkpoint (stored under <output>/.mdtx-state).")
    parser.add_argument("--serve", action="store_true", help="Run as an MCP server on stdio so AI clients (ZCode/Claude Desktop/Cursor) can call mdtx as a tool. Requires the mdtx[mcp] extra.")
    parser.add_argument("--ui-port", type=_parse_positive_int, default=None, help="Serve the local web UI on 127.0.0.1:<port> (mdtx[ui] extra).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(logging.DEBUG if args.verbose else logging.INFO)
    try:
        if args.ui_port is not None:
            from src.api.app import run_server

            run_server(args.ui_port)
            return 0
        if args.serve:
            from src.mcp_server.server import serve

            serve()
            return 0
        if args.init_config:
            config_path = initialize_config(args.config, force=args.force_init_config)
            print(f"Config ready: {config_path}")
            return 0
        if not args.paths:
            parser.error("the following arguments are required: paths")
        config = _apply_cli_overrides(args, load_config(args.config))
        _log_startup_config(args, config)
        if args.eval:
            exit_code = 0
            for path in args.paths:
                for target_lang in config.target_languages:
                    result = evaluate_command(path, target_lang, config)
                    exit_code = exit_code or result
            return exit_code
        return translate_command(
            args.paths,
            config.target_languages,
            config,
            output_dir=config.output.directory,
            match_pattern=config.input.file_pattern,
            resume=args.resume,
        )
    except KeyboardInterrupt:
        print("Translation cancelled by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        presentation = present_cli_error(exc, verbose=args.verbose)
        print(presentation.message, file=sys.stderr)
        return presentation.exit_code


if __name__ == "__main__":
    sys.exit(main())
