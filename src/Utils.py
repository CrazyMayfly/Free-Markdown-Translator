import argparse
import logging
import re
import socks
import socket
from tqdm import tqdm
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

# chunk 类型说明：
# - 传统翻译器： (skipped_parts, need_translate_parts, parts_count)
# - LLM（启用上下文窗口时）：(context_before, skipped_parts, need_translate_parts, parts_count, context_after)
SkippedParts: TypeAlias = dict[int, str]
NeedTranslateParts: TypeAlias = dict[int, str]
ChunkBasic: TypeAlias = tuple[SkippedParts, NeedTranslateParts, int]
ChunkWithContext: TypeAlias = tuple[str, SkippedParts, NeedTranslateParts, int, str]
Chunk: TypeAlias = ChunkBasic | ChunkWithContext

# 指定要跳过翻译的“格式/符号”正则表达式（用于把 Markdown 标记从正文中切分出来并原样保留）。
# 注意：不要跳过普通的双引号内容（例如 `"text"`），否则在源文本存在异常引号（如 PDF/OCR 产物）时，
# 会把大段正文误判为“不可翻译”并直接原样输出，导致出现“前后内容没翻译”的现象。
skipped_regexs = [
    r"\*\*。?",
    r'#+',
    r'`[^\u4E00-\u9FFF]*?`',
    r'`',
    r'\|',
    r'^ *-+',
    r'^[\.,\?!;。，？！；、]$',
    '\n',
]
# 非紧凑型语言中需要添加分隔的正则表达式
expands_regexs = [r'`[^`]+?`', r'".*?"', r'\*\*.*?\*\*', r"\[!\[.*?]\(.*?\)]\(.*?\)|!?\[.*?]\(.*?\)"]
pattern = "({})".format("|".join(skipped_regexs))
expands_pattern = "({})".format("|".join(expands_regexs))


class Patterns:
    ImageOrLink = re.compile(r"\[!\[.*?]\(.*?\)]\(.*?\)|!?\[.*?]\(.*?\)")
    DescOrNestedImage = re.compile(r"\[(!\[.*?]\(.*?\))]|\[(.*?)]")
    LinkContent = re.compile(r"\((.*?)\)")
    DigitalOrder = re.compile(r'\d+\. ')
    Expands = re.compile(expands_pattern)
    Skipped = re.compile(pattern)


PUNCTUATION = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""" + '；，。、？ 、【】·！￥…—‘“”’《》\n'
STOP_PUNCTUATION = ".!?。！？：:；;\n"


def is_not_punctuation(sentence: str, is_first_char: bool = False, is_stop: bool = False) -> bool:
    """
    判断句子的第一个字符或最后一个字符是否为标点符号或停止符号
    :param sentence:  待判断的句子
    :param is_first_char:  是否判断第一个字符
    :param is_stop: 判断是否为停止符号
    :return:
    """
    if sentence is None or len(sentence.strip()) == 0:
        return True
    punctuation_set = STOP_PUNCTUATION if is_stop else PUNCTUATION
    return sentence[0 if is_first_char else -1] not in punctuation_set


def shortedPath(path: Path) -> str:
    """
    获取文件的最后两级路径
    :param path: 文件路径
    :return:
    """
    parts = path.parts
    if len(parts) == 1:
        return parts[0]
    return f'{parts[-2]}/{parts[-1]}'


def ensure_unique_output_path(path: Path) -> Path:
    """
    如果目标输出文件已存在，则返回一个带数字后缀的新路径，按 1,2,3... 递增直到不冲突。

    示例：
    - a.md 已存在 -> a.1.md
    - a.1.md 也存在 -> a.2.md
    """
    if not path.exists():
        return path

    i = 1
    while True:
        candidate = path.with_name(f"{path.stem}.{i}{path.suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def get_size(size, factor=1024, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for data_unit in ["", "K", "M", "G", "T", "P"]:
        if size < factor:
            return f"{size:.2f}{data_unit}{suffix}"
        size /= factor


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Free Markdown Translator - translate Markdown documents into multiple languages.\n\n"
            "默认行为：当目标输出文件已存在时跳过该翻译任务。\n"
            "可以通过 --continue / --rewrite 控制已存在输出文件的处理方式。\n"
            "支持多种翻译引擎：传统引擎（google/bing/baidu...）和 LLM 引擎（translator: llm，需在 .env 中配置 LLM_MODEL_URL/LLM_MODEL_NAME/LLM_MODEL_API_KEY）。"
        )
    )
    parser.add_argument(
        '-f',
        metavar="FILE_OR_FOLDER",
        type=Path,
        nargs="+",
        help="要翻译的 Markdown 文档或文件夹路径；可同时指定多个。",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--continue',
        dest="continue_mode",
        action="store_true",
        help="若目标输出文件已存在，则为该文件生成带数字后缀的新文件（例如 a.md -> a.1.md）。",
    )
    mode_group.add_argument(
        '--rewrite',
        action="store_true",
        help="若目标输出文件已存在，则直接覆盖该文件的内容。",
    )
    return parser.parse_args()


def lower_first_char(sentence: str) -> str:
    """
    将句子的首字母转为小写
    :param sentence: 待处理的句子
    :return:
    """
    if not sentence:
        return ""

    # 若句子的首个单词不是全部大写，则将句子的首字母转为小写
    if not sentence.split(' ')[0].isupper():
        sentence = sentence[0].lower() + sentence[1:] if len(sentence) > 1 else sentence.lower()
    return sentence


def set_proxy(proxy: dict) -> None:
    enable_proxy = proxy.get("enable", False)
    if not enable_proxy:
        return
    address = proxy.get("address")
    port = proxy.get("port")
    if not address:
        raise ValueError("Proxy address is required.")
    if not port:
        raise ValueError("Proxy port is required.")
    username = str(proxy.get("username")) if proxy.get("username") else None
    password = str(proxy.get("password")) if proxy.get("password") else None
    # 设置代理
    socks.set_default_proxy(socks.SOCKS5, address, port, username=username, password=password)
    # 将socket替换为经过代理的socket
    socket.socket = socks.socksocket
    logging.info(f"Proxy has been set to {address}:{port}")


def expand_part(part: str, parts: list[str], position: int, last_char: str) -> str:
    """
    根据part的内容和位置，判断是否需要在part前后添加空格
    :param part: 待处理的part
    :param parts: 所有的part
    :param position: 当前part的位置
    :param last_char: 之前处理完的最后一个字符
    :return:
    """
    if part is None:
        return ""

    # 若part位于句首且之前的最后一个字符是逗号，则将part的首字母转为小写
    if position == 0 and last_char in ',，':
        part = lower_first_char(part)
    # 若part不位于句首且前一个part的最后一个字符不是停止符号，则将part的首字母转为小写
    if position != 0 and is_not_punctuation(parts[position - 1], is_stop=True):
        part = lower_first_char(part)

    if Patterns.Expands.search(part):
        # 首个part，检测之前的结果的最后一个字符是否为标点符号
        if position == 0:
            if is_not_punctuation(last_char):
                part = " " + part
        # 最后一个part，检测前一个part的最后一个字符是否为标点符号
        elif position == len(parts) - 1:
            if is_not_punctuation(parts[position - 1]):
                part = " " + part
        # 中间的part，检测前一个part的最后一个字符是否为标点符号，检测后一个part的第一个字符是否为标点符号
        else:
            if is_not_punctuation(parts[position - 1]):
                part = " " + part
            if is_not_punctuation(parts[position + 1], is_first_char=True):
                part = part + " "
    return part


@dataclass
class RawData:
    nodes: list
    chunks: list[Chunk]
    empty_line_position: list[int]
    chars_count: int


class Pbar:
    """
    将全局的进度条和局部的进度条绑定在一起，便于同时更新
    """

    def __init__(self, global_pbar: tqdm, local_pbar: tqdm):
        self.__global_pbar = global_pbar
        self.__local_pbar = local_pbar

    def update(self, size: int):
        self.__local_pbar.update(size)
        with self.__global_pbar.get_lock():
            self.__global_pbar.update(size)

    def local_pbar_finished(self, is_fail: bool = False):
        if is_fail:
            self.__local_pbar.colour = '#F44336'
        self.__local_pbar.close()
        self.__global_pbar.refresh()


class SymbolWidthUtil:
    __half_full_diff = 0xFEE0
    __full_width_symbols = '！＂＃＄％＆＇（）＊＋，－。．／：；＜＝＞？＠［＼］＾＿｀｛｜｝～‘’”“【】《》￥、'
    # 注意：字符串里包含反斜杠，需要写成 `\\`，否则会触发 Python 的无效转义告警
    __half_width_symbols = '!"#$%&\'()*+,-../:;<=>?@[\\]^_`{|}~\'\'""[]<>$,'
    __full_half_symbol_map = {full: half for full, half in zip(__full_width_symbols, __half_width_symbols)}
    __half_full_symbol_map = {half: full for full, half in zip(__full_width_symbols, __half_width_symbols)}

    @staticmethod
    def __full_to_half_symbol(char: str) -> str:
        return SymbolWidthUtil.__full_half_symbol_map.get(char, char)

    @staticmethod
    def __half_to_full_symbol(char):
        return chr(ord(char) + SymbolWidthUtil.__half_full_diff)

    @staticmethod
    def half_to_full(text: str) -> str:
        """
        将半角符号转换为全角符号
        :param text: 待转换的文本
        :return:
        """
        chars = [SymbolWidthUtil.__half_to_full_symbol(char) for char in text]
        return ''.join(chars)

    @staticmethod
    def full_to_half(text: str) -> str:
        """
        将全角符号转换为半角符号
        :param text: 待转换的文本
        :return:
        """
        chars = [SymbolWidthUtil.__full_to_half_symbol(char) for char in text]
        return ''.join(chars)
