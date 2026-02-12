import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging
from colorlog import ColoredFormatter

# 屏蔽第三方库的噪音日志（例如 OpenAI SDK / httpx 的请求日志）
class _SuppressHttpRequestLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        # 典型输出：HTTP Request: POST https://... "HTTP/1.1 200 OK"
        if isinstance(msg, str) and msg.startswith("HTTP Request:"):
            return False
        return True

# 创建一个自定义的日志处理器来设置日志颜色
formatter = ColoredFormatter(
    "%(blue)s%(asctime)s %(log_color)s[%(levelname)-7s]%(reset)s %(blue)s[%(threadName)-12s] %(log_color)s%(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'white',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
)
# 创建控制台处理器并设置格式
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.addFilter(_SuppressHttpRequestLogFilter())
logger = logging.getLogger()
# 设置日志级别
logger.setLevel(logging.INFO)
# 将处理器添加到日志记录器
logger.addHandler(console_handler)

# 降低第三方库 HTTP 请求日志的输出（避免刷屏）
# 这些 logger 常见于 openai-python(>=1.x) 以及其底层 httpx/httpcore
for _name in ("openai", "openai._base_client", "httpx", "httpcore"):
    logging.getLogger(_name).setLevel(logging.WARNING)

# 支持的翻译引擎
SUPPORTED_TRANSLATORS = {"google", "baidu", "bing", "sogou", "youdao", 'niutrans', 'mymemory', 'alibaba', 'tencent',
                         'modernmt', 'volcengine', 'iciba', 'iflytek', 'lingvanex', 'yandex', 'itranslate', 'systran',
                         'argos', 'apertium', 'reverso', 'cloudtranslation', 'qqtransmart', 'translateCom',
                         'tilde', 'qqfanyi', 'translateme', 'llm'}


@dataclass
class Configration:
    insert_warnings: bool
    src_language: str
    warnings_mapping: dict
    translator: str
    target_langs: list
    compact_langs: list
    src_filenames: list
    threads: int
    proxy: dict
    front_matter_transparent_keys: tuple
    front_matter_key_value_keys: tuple
    front_matter_key_value_array_keys: tuple
    # --- chunking / LLM context window ---
    # 单个 chunk 的目标字符数（按 len(line) 累加的近似值）
    chunk_size_chars: int = 500
    # 仅在 translator=llm 时生效：给每个 chunk 额外提供上下文行数（不回填翻译）
    llm_context_before_lines: int = 5
    llm_context_after_lines: int = 5
    # 可选：LLM 翻译器配置（api_base, model, api_key, temperature, max_tokens）；不配置则从 .env 读取
    llm_config: Optional[dict] = None


def get_default_config() -> Configration:
    # 控制是否在文章前面添加机器翻译的Warning
    insert_warnings = True
    # 源语言，auto表示由谷歌自动识别
    src_language = "auto"
    # 配置目标语言及其warning，默认按照定义顺序翻译为下面语言
    warnings_mapping = {
        'zh': "警告：本文由机器翻译生成，可能导致质量不佳或信息有误，请谨慎阅读！",
        'en': 'Warning: This page is translated by MACHINE, which may lead to POOR QUALITY or INCORRECT INFORMATION, '
              'please read with CAUTION!'
    }
    # 指定目标语言
    target_langs = warnings_mapping.keys()
    # 紧凑型语言，解决英语等非紧凑型语言的分隔问题
    compact_langs = ['zh-TW', 'ja']
    translator = "google"
    # 文件目录下需要翻译的文档的名称
    src_filenames = ['index', 'README', '_index']
    # markdown中Front Matter不用翻译的部分
    front_matter_transparent_keys = ('date:', 'slug:', 'toc', 'image', 'comments', 'readingTime', 'menu:', '    main:',
                                     '        weight:', '        params:', '            icon:', 'links:',
                                     '    website:', '    image:', 'layout:', 'outputs:', '    - html', '    - json',
                                     'license:', '#', 'style:', '    background:', '    color:')
    # Front Matter中需要以Key-Value形式翻译的部分
    front_matter_key_value_keys = ('title:', 'description:', '        name:', '  - title:', '    description:')
    # Front Matter中以Key-Value—Arrays形式翻译
    front_matter_key_value_array_keys = ('tags:', 'categories:', 'keywords:')
    return Configration(insert_warnings=insert_warnings, src_language=src_language, warnings_mapping=warnings_mapping,
                        target_langs=list(target_langs), compact_langs=compact_langs, threads=-1,
                        src_filenames=src_filenames, front_matter_transparent_keys=front_matter_transparent_keys,
                        front_matter_key_value_keys=front_matter_key_value_keys, translator=translator,
                        front_matter_key_value_array_keys=front_matter_key_value_array_keys, proxy={'enable': False},
                        chunk_size_chars=500, llm_context_before_lines=0, llm_context_after_lines=0, llm_config=None)


def get_config(config_path: str) -> Configration:
    """
    读取配置文件，若配置文件不存在或配置有误则使用默认配置

    :param config_path: 配置文件路径
    :return:
    """
    # 如果配置文件不存在，则使用默认配置
    config_file = Path(config_path)
    if not config_file.exists() or not config_file.is_file():
        logging.warning(f"Config file not found, use default config.")
        return get_default_config()
    # 读取配置文件
    try:
        with config_file.open(mode='r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        # 兼容旧配置：为新增字段设置默认值（避免缺字段直接 TypeError）
        data.setdefault("chunk_size_chars", 500)
        data.setdefault("llm_context_before_lines", 0)
        data.setdefault("llm_context_after_lines", 0)
        data.setdefault("llm_config", None)
        translator: str = data.get("translator")
        if translator is None:
            logging.warning(f"Translator not configured, use google translator.")
            data["translator"] = "google"
        elif translator.lower() not in SUPPORTED_TRANSLATORS:
            logging.warning(f"Unsupported translator: {translator}, use google translator.")
            data["translator"] = "google"
        return Configration(**data)
    except Exception as e:
        logging.warning(f"Failed to load config file: {config_file}: {e}")
        return get_default_config()


# 使用与 config.py 同一目录下的 config.yaml 文件
config_file_path = Path(__file__).parent / "config.yaml"
config = get_config(str(config_file_path))
