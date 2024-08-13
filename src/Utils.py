import argparse
import re
from pathlib import Path

from config import config


class Patterns:
    ImageOrLink = re.compile(r"\[!\[.*?]\(.*?\)]\(.*?\)|!?\[.*?]\(.*?\)")
    DescOrNestedImage = re.compile(r"\[(!\[.*?]\(.*?\))]|\[(.*?)]")
    LinkContent = re.compile(r"\((.*?)\)")
    DigitalOrder = re.compile(r'\d+\. ')
    Expands = re.compile(config.expands_pattern)


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
