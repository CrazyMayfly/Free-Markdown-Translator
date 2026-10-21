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
    # document: reuse entries only within the same document content (default,
    # prevents context bleed across documents); global: reuse across documents.
    scope: str = "document"
    # Fuzzy matching over stored entries: near-identical sources are reused
    # directly, close matches are injected as few-shot examples.
    fuzzy_examples: bool = True
    fuzzy_reuse_threshold: float = 0.97
    fuzzy_example_threshold: float = 0.70
    # Stored entries below this confidence are never reused (judge feedback
    # downweights weak segments to 0).
    reuse_min_confidence: float = 0.3
    # Persistent glossary accumulated across runs (human entries win).
    glossary_persist: bool = True
    glossary_path: str = ".mdtx/glossary.sqlite3"
    # Persistent document-brief cache (summary/glossary reused across runs).
    brief_path: str = ".mdtx/briefs.sqlite3"


@dataclass
class PipelineConfig:
    mode: str = "balanced"
    enable_review: bool = False
    enable_format_guard: bool = False
    fail_on_validation_error: bool = True
    # Estimated source tokens per bundle above which a bundle is reviewed
    # automatically in balanced mode. Counted in tokens (see
    # src/core/tokens.py) so the trigger does not drift with the language.
    review_min_bundle_tokens: int = 1200
    review_confidence_threshold: float = 0.85
    # Reflect->improve rounds per bundle; rounds > 1 re-verify every fix.
    review_max_rounds: int = 2
    # Document-level glossary extraction + post-translation harmonization.
    enable_glossary: bool = True
    # Deterministic semantic sentinels (placeholder/number parity, length
    # ratio); findings force a review of the affected bundle.
    enable_sentinels: bool = True
    sentinel_min_length_ratio: float = 0.35
    sentinel_max_length_ratio: float = 3.0
    # Translate each section's first bundle sequentially (anchor), then run
    # the rest in parallel carrying the anchor's real translations.
    enable_anchor_scheduling: bool = True
    # Optional separate models for review/judging (breaks self-review bias).
    reviewer_model: str = ""
    judge_model: str = ""
    # Optional per-mode model routing. Empty means provider.model. The brief
    # model reads the whole document once and produces the summary/glossary.
    fast_model: str = ""
    quality_model: str = ""
    brief_model: str = ""
    # Pull-style context: the translator may request deeper translation-memory
    # search for specific segments; the bundle is then translated once more.
    enable_context_pull: bool = True
    # Document-level final edit (cross-bundle discourse review) in quality mode.
    enable_final_edit: bool = True
    final_edit_max_segments: int = 300


@dataclass
class SegmentationConfig:
    # Hard ceiling for one bundle (and for one segment after line splitting),
    # counted in estimated source tokens. Bundles are packed along Markdown
    # structure first; this only decides when a structural block is too large
    # and has to be split by line.
    #
    # 4000 is about half of the default provider.max_tokens (8000). Translated
    # output costs roughly as many tokens as the source, so this leaves room
    # for the JSON envelope and for one retry without hitting the cap. Raise it
    # together with max_tokens, not on its own.
    max_bundle_tokens: int = 4000
    # Merge small sections/trailing bundles until they reach this many tokens.
    # Roughly the fixed prompt overhead (system + schema + context), so a
    # bundle can carry at least as much translatable text as scaffolding.
    # 0 disables the merge.
    min_bundle_tokens: int = 1000


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
            "review_min_bundle_tokens": 1200,
            "review_confidence_threshold": 0.85,
            "review_max_rounds": 2,
            "enable_glossary": True,
            "enable_sentinels": True,
            "sentinel_min_length_ratio": 0.35,
            "sentinel_max_length_ratio": 3.0,
            "enable_anchor_scheduling": True,
            "reviewer_model": "",
            "judge_model": "",
            "fast_model": "",
            "quality_model": "",
            "brief_model": "",
            "enable_context_pull": True,
            "enable_final_edit": True,
            "final_edit_max_segments": 300,
        },
        "segmentation": {
            "max_bundle_tokens": 4000,
            "min_bundle_tokens": 1000,
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
            "scope": "document",
            "fuzzy_examples": True,
            "fuzzy_reuse_threshold": 0.97,
            "fuzzy_example_threshold": 0.70,
            "reuse_min_confidence": 0.3,
            "glossary_persist": True,
            "glossary_path": ".mdtx/glossary.sqlite3",
            "brief_path": ".mdtx/briefs.sqlite3",
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
  # fast: 省 token/提速；balanced: 默认；quality: 最高质量（strict 为兼容别名）。
  mode: balanced
  # 强制开启审校 Agent。关闭时，balanced 只审可疑包，quality 全量审校。
  enable_review: false
  # 强制开启格式修复 Agent。关闭时，balanced/quality 遇到校验失败仍可能触发修复。
  enable_format_guard: false
  # 输出校验失败时是否直接报错。
  fail_on_validation_error: true
  # balanced 模式下，bundle 估算 token 达到该值才进入审校候选（不再按段数触发）。
  review_min_bundle_tokens: 1200
  # 翻译结果置信度低于该值时触发审校。
  review_confidence_threshold: 0.85
  # 每个文本包的 反思->修复 轮数；大于 1 时每轮修复后会对修复过的段落复核一次。
  review_max_rounds: 2
  # 文档级术语表：译前抽取术语并在所有文本包间强制统一，译后自动修正不一致的译法。
  enable_glossary: true
  # 确定性语义哨兵：占位符/数字守恒与长度比检查，命中即强制审校该文本包（零 LLM 成本）。
  enable_sentinels: true
  # 哨兵长度比上下限（译文/源文字符数）。
  sentinel_min_length_ratio: 0.35
  sentinel_max_length_ratio: 3.0
  # 锚点-并行混合调度：每章首个文本包先串行翻译（锚点），其余并行并携带锚点已译文本。
  enable_anchor_scheduling: true
  # 审校/评审可选用不同模型（留空 = 与翻译同模型），避免自我审校偏好。
  reviewer_model: ""
  judge_model: ""
  # 分模式模型路由（留空 = provider.model）。
  fast_model: ""
  quality_model: ""
  # 文档 Brief 模型：读全文生成大意/术语/章节摘要（留空 = provider.model）。
  brief_model: ""
  # 上下文按需拉取：翻译模型可请求对特定段落做更深的翻译记忆检索，随后重译该文本包。
  enable_context_pull: true
  # 文档级终审（quality 模式）：跨文本包审阅指代/衔接/术语一致性并修正（final_edit 调用）。
  enable_final_edit: true
  # 终审最多覆盖的段落数（控制成本）。
  final_edit_max_segments: 300

# 分段策略。先按 Markdown 结构（标题/列表/表格/引用）打包，超长块再按行拆分。
# 预算单位是估算 token 而不是字符：同样 6000 字符，中文约 4200 token、英文约 1800 token，
# 用字符做预算会让中英文的实际风险差 2 倍以上。
segmentation:
  # 单个文本包的硬上限（估算源 token），也是超长块按行拆分的阈值。
  # 4000 约为 provider.max_tokens（默认 8000）的 50%：译文 token 数与源文大致相当，
  # 剩下的余量留给 JSON 封套和一次重试。要调大请连同 max_tokens 一起调。
  max_bundle_tokens: 4000
  # 小章节/尾包合并到该 token 数为止；0 表示不合并。
  # 约等于每包固定 prompt 开销，保证正文至少和脚手架一样多。
  min_bundle_tokens: 1000

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
  # document = 仅在同一文档内复用（默认，避免跨文档语境错配）；global = 跨文档复用。
  scope: document
  # 模糊匹配：源文高度相似的历史条目直接复用；较相似的作为 few-shot 示例注入 prompt。
  fuzzy_examples: true
  # 相似度达到该值直接复用（0-1，字符三元组 Jaccard）。
  fuzzy_reuse_threshold: 0.97
  # 相似度达到该值作为 few-shot 示例注入。
  fuzzy_example_threshold: 0.70
  # 记忆条目置信度低于该值时不复用（judge 弱段会被降权到 0）。
  reuse_min_confidence: 0.3
  # 持久化术语表：跨运行累积，人工条目（origin=user）永远优先于模型投票。
  glossary_persist: true
  glossary_path: .mdtx/glossary.sqlite3
  # 文档 Brief 缓存（跨运行复用 summary/术语）。
  brief_path: .mdtx/briefs.sqlite3
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


_DEPRECATED_KEYS = {
    ("segmentation", "max_bundle_segments"): (
        "bundles are packed along Markdown structure; segment count no longer controls chunking"
    ),
    ("segmentation", "section_align_min_chars"): (
        "headings are structural boundaries now; small bundles are merged via min_bundle_tokens"
    ),
    ("segmentation", "max_bundle_chars"): (
        "budgets are counted in tokens now; rename to max_bundle_tokens (6000 chars is roughly "
        "1800 tokens of English or 4200 tokens of Chinese)"
    ),
    ("segmentation", "min_bundle_chars"): (
        "budgets are counted in tokens now; rename to min_bundle_tokens (600 chars is roughly "
        "180 tokens of English or 420 tokens of Chinese)"
    ),
    ("pipeline", "review_min_bundle_chars"): (
        "budgets are counted in tokens now; rename to review_min_bundle_tokens (1600 chars is "
        "roughly 1200 tokens of Chinese)"
    ),
    ("pipeline", "review_min_segments"): (
        "balanced review is now risk-driven; bundle token size, confidence and sentinel findings "
        "decide whether a bundle is reviewed"
    ),
}


def _filter_known_keys(section: dict[str, Any], config_type, section_name: str) -> dict[str, Any]:
    allowed = {item.name for item in fields(config_type)}
    unknown = sorted(set(section) - allowed)
    if unknown:
        for key in unknown:
            reason = _DEPRECATED_KEYS.get((section_name, key))
            if reason:
                logging.warning("Deprecated config key %s.%s ignored: %s", section_name, key, reason)
            else:
                logging.warning("Ignoring unsupported config key %s.%s", section_name, key)
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
