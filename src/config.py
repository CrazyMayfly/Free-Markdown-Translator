import yaml
from dataclasses import dataclass
from pathlib import Path
import logging
from colorlog import ColoredFormatter

# 创建一个自定义的日志处理器来设置日志颜色
formatter = ColoredFormatter(
    "%(blue)s%(asctime)s %(log_color)s[%(levelname)-5s]%(reset)s %(blue)s[%(threadName)s] %(log_color)s%(message)s",
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
logger = logging.getLogger()
# 设置日志级别
logger.setLevel(logging.INFO)
# 将处理器添加到日志记录器
logger.addHandler(console_handler)

# 指定要跳过翻译的字符的正则表达式，分别为加粗符号、在``中的非中文字符，`，用于过滤表格的符号，换行符
skipped_regexs = [r"\*\*。?", r'#+', r'`[^\u4E00-\u9FFF]*?`', r'`', r'"[^\u4E00-\u9FFF]*?"', r'-+', r'\|', '\n']
# 非紧凑型语言中需要添加分隔的正则表达式
expands_regexs = [r'`[^`]+?`', r'".*?"', r'\*\*.*?\*\*', r'!\[.*?\]\(.*?\)', r'\[.*?\]\(.*?\)']
# pattern = "|".join(map(re.escape, self.skipped_chars))
pattern = "({})".format("|".join(skipped_regexs))
expands_pattern = "({})".format("|".join(expands_regexs))

# 支持的翻译引擎
SUPPORTED_TRANSLATORS = {"google", "baidu", "bing", "sogou", "youdao", 'niutrans', 'mymemory', 'alibaba', 'tencent',
                         'modernmt', 'volcengine', 'iciba', 'iflytek', 'lingvanex', 'yandex', 'itranslate', 'systran',
                         'argos', 'apertium', 'reverso', 'deepl', 'cloudtranslation', 'qqtransmart', 'translateCom',
                         'tilde', 'qqfanyi', 'translateme'}


@dataclass
class Configration:
    insert_warnings: bool
    src_language: str
    warnings_mapping: dict
    translator: str
    target_langs: list
    compact_langs: list
    skipped_regexs: list
    expands_regexs: list
    pattern: str
    expands_pattern: str
    src_filenames: list
    front_matter_transparent_keys: tuple
    front_matter_key_value_keys: tuple
    front_matter_key_value_array_keys: tuple


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
                        target_langs=list(target_langs), compact_langs=compact_langs, skipped_regexs=skipped_regexs,
                        expands_regexs=expands_regexs, pattern=pattern, expands_pattern=expands_pattern,
                        src_filenames=src_filenames, front_matter_transparent_keys=front_matter_transparent_keys,
                        front_matter_key_value_keys=front_matter_key_value_keys, translator=translator,
                        front_matter_key_value_array_keys=front_matter_key_value_array_keys)


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
        translator:str = data.get("translator")
        if translator is None:
            logging.warning(f"Translator not configured, use google translator.")
            data["translator"] = "google"
        elif translator.lower() not in SUPPORTED_TRANSLATORS:
            logging.warning(f"Unsupported translator: {translator}, use google translator.")
            data["translator"] = "google"
        return Configration(**data, skipped_regexs=skipped_regexs, expands_regexs=expands_regexs, pattern=pattern,
                            expands_pattern=expands_pattern)
    except Exception as e:
        logging.warning(f"Failed to load config file: {config_file}: {e}")
        return get_default_config()


config = get_config("config.yaml")
