from __future__ import annotations

import logging
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_DIRNAME = ".mdtx"
DEFAULT_CONFIG_FILENAME = "config.yaml"


@dataclass
class ProviderConfig:
    name: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    model: str = "gpt-5-mini"
    temperature: float = 0.2
    max_tokens: int = 8000
    structured_outputs: str = "auto"
    max_retries: int = 3


@dataclass
class MemoryConfig:
    enabled: bool = True
    path: str = ".mdtx/memory.sqlite3"


@dataclass
class PipelineConfig:
    mode: str = "balanced"
    enable_review: bool = False
    enable_format_guard: bool = False
    fail_on_validation_error: bool = True
    review_min_bundle_chars: int = 1600
    review_min_segments: int = 6
    review_confidence_threshold: float = 0.85


@dataclass
class SegmentationConfig:
    max_bundle_chars: int = 6000
    max_bundle_segments: int = 12


@dataclass
class InputConfig:
    file_pattern: str = "*.md"


@dataclass
class StyleConfig:
    tone: str = "technical"
    preserve_terms: list[str] = field(default_factory=lambda: ["Markdown", "OpenAI", "Python"])
    audience: str = "developers"
    instructions: list[str] = field(
        default_factory=lambda: [
            "Keep protected placeholders unchanged.",
            "Do not alter Markdown control syntax.",
        ]
    )


@dataclass
class OutputConfig:
    directory: str = "output"
    file_suffix_template: str = "{stem}.{lang}.md"
    write_report: bool = True


@dataclass
class ExecutionConfig:
    max_parallel_translations: int = 5


@dataclass
class TranslatorConfig:
    target_languages: list[str] = field(default_factory=lambda: ["english"])
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    segmentation: SegmentationConfig = field(default_factory=SegmentationConfig)
    input: InputConfig = field(default_factory=InputConfig)
    style: StyleConfig = field(default_factory=StyleConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def default_user_config_dir() -> Path:
    return Path.home() / DEFAULT_CONFIG_DIRNAME


def default_user_config_path() -> Path:
    return default_user_config_dir() / DEFAULT_CONFIG_FILENAME


def resolve_config_path(config_path: str | None = None) -> Path | None:
    root = _workspace_root()
    candidates = []
    if config_path:
        candidates.append(Path(config_path).expanduser())
    candidates.extend(
        [
            root / "config.yaml",
            root / "src" / "config.yaml",
            default_user_config_path(),
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _default_config_dict() -> dict[str, Any]:
    return {
        "target_languages": ["english"],
        "provider": {
            "name": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": None,
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-5-mini",
            "temperature": 0.2,
            "max_tokens": 8000,
            "structured_outputs": "auto",
            "max_retries": 3,
        },
        "pipeline": {
            "mode": "balanced",
            "enable_review": False,
            "enable_format_guard": False,
            "fail_on_validation_error": True,
            "review_min_bundle_chars": 1600,
            "review_min_segments": 6,
            "review_confidence_threshold": 0.85,
        },
        "segmentation": {
            "max_bundle_chars": 6000,
            "max_bundle_segments": 12,
        },
        "input": {
            "file_pattern": "*.md",
        },
        "style": {
            "tone": "technical",
            "preserve_terms": ["Markdown", "OpenAI", "Python"],
            "audience": "developers",
            "instructions": [
                "Keep protected placeholders unchanged.",
                "Do not alter Markdown control syntax.",
            ],
        },
        "output": {
            "directory": "output",
            "file_suffix_template": "{stem}.{lang}.md",
            "write_report": True,
        },
        "execution": {
            "max_parallel_translations": 5,
        },
        "memory": {
            "enabled": True,
            "path": ".mdtx/memory.sqlite3",
        },
    }


def render_default_config_yaml() -> str:
    return """# Free Markdown Translator 配置文件

# 目标语言列表。支持一次翻译为多个语言。
target_languages:
  - english

# 大模型服务配置。当前实现为 OpenAI 兼容接口。
provider:
  name: openai
  base_url: https://api.openai.com/v1
  # 推荐通过环境变量提供密钥；如需直填，可写在 api_key。
  api_key:
  api_key_env: OPENAI_API_KEY
  model: gpt-5-mini
  # 温度越低，输出越稳定。
  temperature: 0.2
  # 单次响应的最大 token 数。
  max_tokens: 8000
  # 结构化输出模式：auto = 优先 json_schema 受限解码、端点不支持时自动降级；
  # on = 强制 json_schema；off = 始终使用 json_object。
  structured_outputs: auto
  # 瞬时错误（限流 429/5xx/超时）自动重试次数，指数退避并尊重 Retry-After。
  max_retries: 3

# 翻译流程控制。
pipeline:
  # fast: 更快；balanced: 默认；strict: 格式更严格。
  mode: balanced
  # 强制开启审校 Agent。关闭时，balanced/strict 仍可能按条件触发agent格式审校。
  enable_review: false
  # 强制开启格式修复 Agent。关闭时，balanced/strict 遇到校验失败仍可能触发修复。
  enable_format_guard: false
  # 输出校验失败时是否直接报错。
  fail_on_validation_error: true
  # 以下为 balanced 模式下按条件触发审校的阈值。
  # bundle 字符数达到该值时触发审校。
  review_min_bundle_chars: 1600
  # bundle 段落数达到该值时触发审校。
  review_min_segments: 6
  # 翻译结果置信度低于该值时触发审校。
  review_confidence_threshold: 0.85

# 分段策略。控制一次发送给模型的文本包大小。
segmentation:
  max_bundle_chars: 6000
  max_bundle_segments: 12

# 输入规则。
input:
  # 当传入目录时，递归匹配需要翻译的文件。
  file_pattern: "*.md"

# 文风与术语约束，会注入翻译上下文。
style:
  tone: technical
  audience: developers
  preserve_terms:
    - Markdown
    - OpenAI
    - Python
  instructions:
    - Keep protected placeholders unchanged.
    - Do not alter Markdown control syntax.

# 输出设置。
output:
  # 所有翻译结果会输出到这个目录下，并尽量保留原目录层级。
  directory: output
  # 可用变量：{stem} 原文件名，{lang} 目标语言缩写。
  file_suffix_template: "{stem}.{lang}.md"
  # 是否同时写出 *.report.json 报告。
  write_report: true

# 执行设置。
execution:
  # 全局 bundle 级最大并行翻译数。
  max_parallel_translations: 5

# 翻译记忆设置。
memory:
  # 启用后，完全相同的段落（同源文、同语言、同模型、同风格配置）直接复用历史译文，跳过 LLM 调用。
  enabled: true
  # SQLite 记忆库路径。
  path: .mdtx/memory.sqlite3
"""


def initialize_config(config_path: str | None = None, force: bool = False) -> Path:
    destination = Path(config_path).expanduser() if config_path else default_user_config_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return destination
    destination.write_text(render_default_config_yaml(), encoding="utf-8")
    return destination


def _load_yaml_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _filter_known_keys(section: dict[str, Any], config_type, section_name: str) -> dict[str, Any]:
    allowed = {item.name for item in fields(config_type)}
    unknown = sorted(set(section) - allowed)
    if unknown:
        logging.warning("Ignoring unsupported config keys in %s: %s", section_name, ", ".join(unknown))
    return {key: value for key, value in section.items() if key in allowed}


def load_config(config_path: str | None = None) -> TranslatorConfig:
    loaded_path = resolve_config_path(config_path)
    loaded: dict[str, Any] | None = None
    if loaded_path is not None:
        loaded = _load_yaml_file(loaded_path)
    else:
        loaded_path = initialize_config()
        loaded = _load_yaml_file(loaded_path)
        logging.info("No config file found. Created default config at %s", loaded_path)

    data = _default_config_dict()
    if loaded_path is not None and loaded is not None:
        data = _merge_dict(data, loaded)
        logging.info("Loaded config from %s", loaded_path)

    return TranslatorConfig(
        target_languages=list(data["target_languages"]),
        provider=ProviderConfig(
            **_filter_known_keys(data["provider"], ProviderConfig, "provider"),
        ),
        pipeline=PipelineConfig(**_filter_known_keys(data["pipeline"], PipelineConfig, "pipeline")),
        segmentation=SegmentationConfig(**_filter_known_keys(data["segmentation"], SegmentationConfig, "segmentation")),
        input=InputConfig(**_filter_known_keys(data["input"], InputConfig, "input")),
        style=StyleConfig(**_filter_known_keys(data["style"], StyleConfig, "style")),
        output=OutputConfig(**_filter_known_keys(data["output"], OutputConfig, "output")),
        execution=ExecutionConfig(**_filter_known_keys(data["execution"], ExecutionConfig, "execution")),
        memory=MemoryConfig(**_filter_known_keys(data["memory"], MemoryConfig, "memory")),
    )
