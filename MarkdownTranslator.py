import argparse
import os
import pathlib
import threading
import time

from GoogleTranslator import GoogleTrans, logging_lock
from Nodes import *
from config import *


class MdTranslater:
    def __init__(self, src_lang, base_dir, src_filename_body):
        self.src_lang = src_lang
        self.base_dir = base_dir
        self.src_filename_body = src_filename_body
        self.src_filename = os.path.join(base_dir, src_filename_body + '.md')
        self.dest_lang = ''
        self.trans = GoogleTrans()
        self.insert_warnings = insert_warnings

    def translate_with_skipped_chars(self, text, src_lang, dest_lang):
        """
        翻译时忽略在config.py中配置的正则表达式，翻译后保证格式不变
        :param text: 本次翻译的文本
        :return: 翻译后的文本
        """
        parts = re.split(pattern, text)
        # 跳过的部分
        skipped_parts = {}
        # 需要翻译的部分
        translated_parts = {}
        idx = 0
        for part in parts:
            if len(part) == 0:
                continue
            is_translated = True
            for skipped_char in skipped_regexs:
                if re.match(skipped_char, part):  # 原封不动地添加跳过的字符
                    skipped_parts.update({idx: part})
                    is_translated = False
                    break
            if is_translated:
                translated_parts.update({idx: part})
            idx += 1
        # 组装翻译
        text = '\n'.join(translated_parts.values())
        translate = self.trans.translate(text, src_lang, dest_lang)
        # 确保api接口返回了结果
        while translate is None:
            translate = self.trans.translate(text, src_lang, dest_lang)
        translated_text = translate.split('\n')
        idx1 = 0
        # 更新翻译部分的内容
        for key in translated_parts.keys():
            translated_parts[key] = translated_text[idx1]
            idx1 += 1
        total_parts = {}
        total_parts.update(skipped_parts)
        total_parts.update(translated_parts)
        translated_text = ''
        # 拼接回字符串
        for i in range(0, idx):
            translated_text += total_parts[i]
        splitlines = translated_text.splitlines()[1:-1]
        translated_text = '\n'.join(splitlines) + '\n'
        return translated_text

    def translate_in_batches(self, lines, src_lang, dest_lang):
        """
        分批次翻译
        """
        # 需在头尾添加字符以保证Google Translate Api不会把空行去除
        tmp = "BEGIN\n"
        translated_text = ""
        for line in lines:
            tmp = tmp + line + '\n'
            # 控制每次发送的数据量
            if len(tmp) > 500:
                tmp += 'END'
                translated_text += self.translate_with_skipped_chars(tmp, src_lang, dest_lang)
                tmp = "BEGIN\n"

        if len(tmp) > 0:
            tmp += 'END'
            translated_text += self.translate_with_skipped_chars(tmp, src_lang, dest_lang)
        return translated_text

    def generate_nodes(self, src_lines):
        """
        扫描每行，依次为每行生成节点
        """
        is_front_matter = False
        # 在```包裹的代码块中
        is_code_block = False
        nodes = []
        for line in src_lines:
            if line.strip() == '---':
                is_front_matter = not is_front_matter
                nodes.append(TransparentNode(line))
                # 添加头部的机器翻译警告
                if not is_front_matter and self.insert_warnings:
                    nodes.append(TransparentNode(f'\n> {warnings_mapping[self.dest_lang]}\n'))
                    self.insert_warnings = False
                continue
            if line.startswith('```'):
                is_code_block = not is_code_block
                nodes.append(TransparentNode(line))
                continue

            if is_front_matter:
                if line.startswith(front_matter_key_value_keys):
                    nodes.append(KeyValueNode(line))
                elif line.startswith(front_matter_transparent_keys):
                    nodes.append(TransparentNode(line))
                elif line.startswith(front_matter_key_value_array_keys):
                    nodes.append(KeyValueArrayNode(line))
                else:
                    nodes.append(SolidNode(line))
            elif is_code_block:
                nodes.append(TransparentNode(line))
            else:
                if len(line.strip()) == 0 or line.startswith(('<audio', '<img ')):  # 空行
                    nodes.append(TransparentNode(line))
                elif re.search('!\[.*?\]\(.*?\)', line) is not None:  # 图片
                    nodes.append(ImageNode(line))
                elif re.search('\[.*?\]\(.*?\)', line) is not None:
                    nodes.append(LinkNode(line))
                elif line.strip().startswith('#'):  # 标题
                    nodes.append(TitleNode(line))
                    # 一级标题
                    if line.strip().startswith('# ') and self.insert_warnings:
                        nodes.append(TransparentNode(f'\n> {warnings_mapping[self.dest_lang]}\n'))
                        self.insert_warnings = False

                else:  # 普通文字
                    nodes.append(SolidNode(line))
        return nodes

    def translate_lines(self, src_lines, src_lang, dest_lang):
        """
        执行数据的拆分翻译组装
        """
        self.dest_lang = dest_lang
        nodes = self.generate_nodes(src_lines)
        # 待翻译md文本
        src_md_text = ''
        for node in nodes:
            trans_buff = node.get_trans_buff()
            if trans_buff:
                src_md_text += trans_buff
        src_lines = src_md_text.splitlines()
        translated_text = self.translate_in_batches(src_lines, src_lang, dest_lang)
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
                node.value = '\n'.join(translated_lines[start_pos:start_pos + node_trans_lines])
                start_pos += node_trans_lines

        final_markdown = ''
        for node in nodes:
            final_markdown += node.compose()
        return final_markdown

    def translate_to(self, dest_lang):
        """
        执行文件的读取、翻译、写入
        """
        dest_filename = os.path.join(self.base_dir, f'{self.src_filename_body}.{dest_lang}.md')
        if not os.path.exists(self.src_filename):
            print('src file ', self.src_filename, ' not exist! skip.')
            return
        with logging_lock:
            print(threading.current_thread().name, ' is translating file ', self.src_filename, ' to ', dest_filename)
        with open(self.src_filename, encoding='utf-8') as src_filename_data:
            src_lines = src_filename_data.readlines()
        if dest_lang != 'zh-tw':
            src_lines_tmp = []
            for line in src_lines:
                src_lines_tmp.append(line.replace('。', '. '))
            src_lines = src_lines_tmp
        src_lines.append('\n')
        final_md_text = self.translate_lines(src_lines, self.src_lang, dest_lang)
        with open(dest_filename, 'w', encoding='utf-8') as outfile:
            outfile.write(final_md_text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Markdown Translator, just input folders and you will get all the langs you want.')
    parser.add_argument('folders', metavar='folder', type=pathlib.Path, nargs='+',
                        help='the markdown files in folders to be translated.')
    args = parser.parse_args()
    base_dirs = args.folders
    # 可以一次性将多个文件夹添加入队列
    # base_dirs = input('Please input the folders: ').split(', ')
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            print(f'{base_dir} does not exist, Skipped!!!')
            continue
        print(f'Current folder is : {base_dir}')
        # 每个文件夹下至少存在一个配置中的文件名
        count = 0
        for detect_filename in detect_filenames:
            src_filename = os.path.join(base_dir, detect_filename + '.md')
            if os.path.exists(src_filename):
                count += 1
        while count == 0:
            count = 0
            base_dir = input(f'Can not find {detect_filenames}, please enter the valid folder again: ')
            for detect_filename in detect_filenames:
                src_filename = os.path.join(base_dir, detect_filename + '.md')
                if os.path.exists(src_filename):
                    count += 1

        for detect_filename in detect_filenames:
            src_filename = os.path.join(base_dir, detect_filename + '.md')
            if os.path.exists(src_filename):
                # 将要被翻译至的语言
                waiting_to_be_translated_langs = []
                for lang in dest_langs:
                    dest_filename = os.path.join(base_dir, f'{detect_filename}.{lang}.md')
                    if os.path.exists(dest_filename):
                        if input(f'{dest_filename} already exists, whether to continue(y/n): ') != 'y':
                            continue
                    waiting_to_be_translated_langs.append(lang)
                # 使用多线程翻译
                start = time.time()
                threads = []
                for lang in waiting_to_be_translated_langs:
                    translater = MdTranslater('zh', base_dir, detect_filename)
                    t = threading.Thread(target=translater.translate_to, args=(lang,))
                    t.start()
                    threads.append(t)

                for t in threads:
                    t.join()
                cost = round(time.time() - start, 2)
                print(f'Total time cost: {cost}s, average per lang cost: '
                      f'{round(cost / len(waiting_to_be_translated_langs), 2)}s.\n')
