import argparse
import os
import threading
import time
import concurrent.futures
from pathlib import Path

from GoogleTranslator import GoogleTrans
from Nodes import *
from config import config


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Markdown Translator, just input folders and you will get all the langs you want."
    )
    parser.add_argument(
        "folders",
        metavar="folder",
        type=Path,
        nargs="+",
        help="the markdown files in folders to be translated.",
    )
    return parser.parse_args()


class MdTranslater:
    trans = GoogleTrans()

    def __init__(self, src_lang, args):
        self.__src_lang = src_lang
        self.__args = args
        self.__src_file: Path = ...
        self.__target_lang = ""
        self.__insert_warnings = config.insert_warnings
        self.__executor: concurrent.futures.ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor(
            thread_name_prefix='Translator')

    @staticmethod
    def __preprocessing(target_lang, src_lines):
        if target_lang != "zh-TW":
            src_lines_tmp = []
            for line in src_lines:
                line = line.replace("。", ". ").replace("，", ",")
                src_lines_tmp.append(line)
            src_lines = src_lines_tmp
        src_lines.append("\n")
        return src_lines

    def __translate_with_skipped_chars(self, text, src_lang, target_lang):
        """
        翻译时忽略在config.py中配置的正则表达式，翻译后保证格式不变
        :param text: 本次翻译的文本
        :return: 翻译后的文本
        """
        parts = re.split(config.pattern, text)
        # 跳过的部分
        skipped_parts = {}
        # 需要翻译的部分
        translated_parts = {}
        idx = 0
        for part in parts:
            if len(part) == 0:
                continue
            is_translated = True
            for skipped_char in config.skipped_regexs:
                if re.match(skipped_char, part):  # 原封不动地添加跳过的字符
                    skipped_parts.update({idx: part})
                    is_translated = False
                    break
            if is_translated:
                translated_parts.update({idx: part})
            idx += 1
        # 组装翻译
        text = "\n".join(translated_parts.values())
        translate = self.trans.translate(text, src_lang, target_lang)
        # 确保api接口返回了结果
        while translate is None:
            translate = self.trans.translate(text, src_lang, target_lang)
        translated_text = translate.split("\n")
        idx1 = 0
        # 更新翻译部分的内容
        for key in translated_parts.keys():
            translated_parts[key] = translated_text[idx1]
            idx1 += 1
        total_parts = {}
        total_parts.update(skipped_parts)
        total_parts.update(translated_parts)
        translated_text = ""
        # 拼接回字符串
        for i in range(0, idx):
            translated_text += total_parts[i]
        splitlines = translated_text.splitlines()[1:-1]
        translated_text = "\n".join(splitlines) + "\n"
        return translated_text

    def __translate_in_batches(self, lines, src_lang, target_lang):
        """
        分批次翻译
        """
        # 需在头尾添加字符以保证Google Translate Api不会把空行去除
        tmp = "BEGIN\n"
        translated_text = ""
        for line in lines:
            tmp = tmp + line + "\n"
            # 控制每次发送的数据量
            if len(tmp) > 500:
                tmp += "END"
                translated_text += self.__translate_with_skipped_chars(
                    tmp, src_lang, target_lang
                )
                tmp = "BEGIN\n"

        if len(tmp) > 0:
            tmp += "END"
            translated_text += self.__translate_with_skipped_chars(
                tmp, src_lang, target_lang
            )
        return translated_text

    def __generate_nodes(self, src_lines):
        """
        扫描每行，依次为每行生成节点
        """
        is_front_matter = False
        # 在```包裹的代码块中
        is_code_block = False
        # 忽略翻译的部分，实际上和代码块内容差不多，只是连标识符都忽略了
        do_not_trans = False
        nodes = []
        for line in src_lines:
            if line.strip() == "---":
                is_front_matter = not is_front_matter
                nodes.append(TransparentNode(line))
                # 添加头部的机器翻译警告
                if not is_front_matter and self.__insert_warnings:
                    nodes.append(
                        TransparentNode(f"\n> {config.warnings_mapping[self.__target_lang]}\n")
                    )
                    self.__insert_warnings = False
                continue
            if line.startswith("```"):
                is_code_block = not is_code_block
                nodes.append(TransparentNode(line))
                continue
            if line.startswith("__do_not_translate__"):
                do_not_trans = not do_not_trans
                continue

            if is_front_matter:
                if line.startswith(config.front_matter_key_value_keys):
                    nodes.append(KeyValueNode(line))
                elif line.startswith(config.front_matter_transparent_keys):
                    nodes.append(TransparentNode(line))
                elif line.startswith(config.front_matter_key_value_array_keys):
                    nodes.append(KeyValueArrayNode(line))
                else:
                    nodes.append(SolidNode(line))
            elif is_code_block or do_not_trans:
                nodes.append(TransparentNode(line))
            else:
                if len(line.strip()) == 0 or line.startswith(
                        ("<audio", "<img ")
                ):  # 空行
                    nodes.append(TransparentNode(line))
                elif re.search("!\[.*?\]\(.*?\)", line) is not None:  # 图片
                    nodes.append(ImageNode(line))
                elif re.search("\[.*?\]\(.*?\)", line) is not None:
                    nodes.append(LinkNode(line))
                elif line.strip().startswith("#"):  # 标题
                    nodes.append(TitleNode(line))
                    # 一级标题
                    if line.strip().startswith("# ") and self.__insert_warnings:
                        nodes.append(
                            TransparentNode(
                                f"\n> {config.warnings_mapping[self.__target_lang]}\n"
                            )
                        )
                        self.__insert_warnings = False

                else:  # 普通文字
                    nodes.append(SolidNode(line))
        return nodes

    def __translate_lines(self, src_lines, src_lang, target_lang):
        """
        执行数据的拆分翻译组装
        """
        self.__target_lang = target_lang
        nodes = self.__generate_nodes(src_lines)
        # 待翻译md文本
        src_md_text = ""
        for node in nodes:
            trans_buff = node.get_trans_buff()
            if trans_buff:
                src_md_text += trans_buff
        src_lines = src_md_text.splitlines()
        translated_text = self.__translate_in_batches(src_lines, src_lang, target_lang)
        translated_lines = translated_text.splitlines()
        start_pos = 0
        for node in nodes:
            node_trans_lines = node.trans_lines
            if node_trans_lines == 0:
                continue
            elif node_trans_lines == 1:
                node.value = translated_lines[start_pos]
                start_pos += 1
            else:
                node.value = "\n".join(
                    translated_lines[start_pos: start_pos + node_trans_lines]
                )
                start_pos += node_trans_lines

        final_markdown = ""
        for node in nodes:
            final_markdown += node.compose()
        return final_markdown

    def translate_to(self, target_lang):
        """
        执行文件的读取、翻译、写入
        """
        if not self.__src_file.exists():
            print("src file ", self.__src_file.as_posix(), " not exist! skip.")
            return
        target_file = self.__src_file.parent / f'{self.__src_file.stem}.{target_lang}.md'

        print(
            threading.current_thread().name,
            " is translating file ",
            self.__src_file.as_posix(),
            " to ",
            target_file,
        )
        with open(self.__src_file, encoding="utf-8") as src_filename_data:
            src_lines = src_filename_data.readlines()
        # 对数据进行预处理
        src_lines = self.__preprocessing(target_lang, src_lines)
        final_md_text = self.__translate_lines(src_lines, self.__src_lang, target_lang)
        final_markdown = ""
        for line in final_md_text.splitlines():
            if target_lang not in config.compact_langs:
                parts = re.split(config.expands_pattern, line)
                line = ""
                for position, part in enumerate(parts):
                    if not part or len(part) == 0:
                        continue
                    for expands_regex in config.expands_regexs:
                        if re.match(expands_regex, part):
                            if position == 0:
                                part = part + " "
                            elif position == len(parts) - 1:
                                part = " " + part
                            else:
                                part = " " + part + " "
                            break
                    line += part
            final_markdown += line + "\n"
        target_file.write_text(final_markdown, encoding="utf-8")

    def main(self):
        base_dirs = self.__args.folders
        for base_dir in base_dirs:
            if not os.path.exists(base_dir):
                print(f"{base_dir} does not exist, Skipped!!!")
                continue
            print(f"Current folder is : {base_dir}")
            # 每个文件夹下至少存在一个配置中的文件名
            has_src_file = False
            for src_filename in config.src_filenames:
                src_file = Path(base_dir) / (src_filename + '.md')
                print(src_file)
                if src_file.exists():
                    has_src_file = True
                    break

            if not has_src_file:
                print(f"{base_dir} does not contain any file in src_filenames, Skipped!!!")
                continue

            for src_filename in config.src_filenames:
                src_file = Path(base_dir) / (src_filename + '.md')
                if src_file.exists():
                    # 将要被翻译至的语言
                    target_langs = []
                    for lang in config.target_langs:
                        target_file = Path(base_dir) / f'{src_filename}.{lang}.md'
                        if target_file.exists():
                            if (input(f"{target_file.as_posix()} already exists, whether to continue(y/n): ").lower()
                                    != "y"):
                                continue
                        target_langs.append(lang)
                    # 使用多线程翻译
                    self.__parallel_translate(src_file, target_langs)

    def __parallel_translate(self, src_file: Path, target_langs: list) -> None:
        """
        多线程翻译
        :param src_file:  待翻译的源文件
        :param target_langs:  待翻译的目标语言
        :return:
        """
        if len(target_langs) == 0:
            return
        start = time.time()
        self.__src_file = src_file
        # 使用多线程翻译
        futures = [self.__executor.submit(self.translate_to, target_lang) for target_lang in
                   target_langs]
        # 等待所有线程结束
        for future in futures:
            while not future.done():
                time.sleep(0.1)
        cost = round(time.time() - start, 2)
        print(
            f"Total time cost: {cost}s, average per lang cost: "
            f"{round(cost / len(target_langs), 2)}s.\n"
        )


if __name__ == "__main__":
    args = get_arguments()
    translater = MdTranslater(config.src_language, args)
    translater.main()
