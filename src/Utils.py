import argparse
import re
from tqdm import tqdm
from dataclasses import dataclass
from pathlib import Path


# 指定要跳过翻译的字符的正则表达式，分别为加粗符号、在``中的非中文字符，`，用于过滤表格的符号，换行符
skipped_regexs = [r"\*\*。?", r'#+', r'`[^\u4E00-\u9FFF]*?`', r'`', r'"[^\u4E00-\u9FFF]*?"', r'\|', r'^ *-+',
                  r'^[\.,\?!;。，？！；、]$', '\n']
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


def is_punctuation(sentence: str, is_first_char: bool = False) -> bool:
    """
    判断句子的第一个字符或最后一个字符是否为标点符号
    :param sentence:  待判断的句子
    :param is_first_char:  是否判断第一个字符
    :return:
    """
    if sentence is None or len(sentence.strip()) == 0:
        return True
    return sentence[0 if is_first_char else -1] in PUNCTUATION


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
        description="Markdown translator, which translates markdown documents to target languages you want."
    )
    parser.add_argument(
        '-f',
        metavar="file/folder",
        type=Path,
        nargs="+",
        help="the markdown documents or folders to translate.",
    )
    return parser.parse_args()


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
    if Patterns.Expands.search(part):
        # 首个part，检测之前的结果的最后一个字符是否为标点符号
        if position == 0:
            if not is_punctuation(last_char):
                part = " " + part
        # 最后一个part，检测前一个part的最后一个字符是否为标点符号
        elif position == len(parts) - 1:
            if not is_punctuation(parts[position - 1]):
                part = " " + part
        # 中间的part，检测前一个part的最后一个字符是否为标点符号，检测后一个part的第一个字符是否为标点符号
        else:
            if not is_punctuation(parts[position - 1]):
                part = " " + part
            if not is_punctuation(parts[position + 1], is_first_char=True):
                part = part + " "
    return part


@dataclass
class RawData:
    nodes: list
    chunks: list[tuple[dict[int, str], dict[int, str], int]]
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
    __half_width_symbols = '!"#$%&\'()*+,-../:;<=>?@[\]^_`{|}~\'\'""[]<>$,'
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
