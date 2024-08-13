import argparse
import re
from pathlib import Path

# 指定要跳过翻译的字符的正则表达式，分别为加粗符号、在``中的非中文字符，`，用于过滤表格的符号，换行符
skipped_regexs = [r"\*\*。?", r'#+', r'`[^\u4E00-\u9FFF]*?`', r'`', r'"[^\u4E00-\u9FFF]*?"', r'\|', r'^ *-+', r'^\.$',
                  r'^,$', '\n']
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


def is_punctuation(sentence: str, is_first_char=False) -> bool:
    """
    判断句子的第一个字符或最后一个字符是否为标点符号
    :param sentence:  待判断的句子
    :param is_first_char:  是否判断第一个字符
    :return:
    """
    if sentence is None or len(sentence.strip()) == 0:
        return True
    return sentence[0 if is_first_char else -1] in PUNCTUATION


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


half_full_diff = 0xFEE0
full_width_symbols = '！＂＃＄％＆＇（）＊＋，－．／：；＜＝＞？＠［＼］＾＿｀｛｜｝～'


def full_to_half_char(ch):
    return chr(ord(ch) - half_full_diff)


def full_width_symbol_to_half_width(text: str) -> str:
    """
    将全角符号转换为半角符号
    :param text:  待转换的文本
    :return:
    """
    return "".join(full_to_half_char(ch) if ch in full_width_symbols else ch for ch in text)
