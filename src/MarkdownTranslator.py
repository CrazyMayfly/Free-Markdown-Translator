import argparse
import copy
import concurrent.futures
import os
import re
from pathlib import Path
from Nodes import *
from config import config
from Utils import Patterns, get_arguments, expand_part, RawData, Pbar, shortedPath, get_size, ensure_unique_output_path
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm


class MdTranslater:
    def __init__(self, args: argparse.Namespace):
        self.__args: argparse.Namespace = args
        # 根据配置选择翻译器
        if config.translator.lower() == 'llm':
            logging.info("Using LLM Translator")
            from llm_translator import LLMTranslator
            self.__trans = LLMTranslator()
        else:
            logging.info(f"Using traditional translator: {config.translator}")
            # 延迟导入：避免仅查看 `-h/--help` 时触发翻译引擎初始化/联网检测
            from Translator import Translator
            self.__trans = Translator()

    @staticmethod
    def __sanitize_filename_token(token: str) -> str:
        """
        将任意字符串压缩为适合文件名的 token。
        - 保留字符：[a-zA-Z0-9._-]
        - 其他字符移除
        """
        token = (token or "").strip()
        # 常见的路径分隔符/空白先替换，避免出现目录穿越或难读文件名
        token = token.replace(os.sep, "-").replace("/", "-").replace("\\", "-").replace(" ", "")
        token = re.sub(r"[^a-zA-Z0-9._-]+", "", token)
        return token or "unknown"

    def __build_target_file(self, src_file: Path, target_lang: str) -> Path:
        """
        根据目标语言与翻译引擎生成输出文件名。
        - 传统引擎：{stem}.{lang}.{engine}.md
        - LLM：{stem}.{lang}.llm.{model}.md
        """
        engine = (config.translator or "google").lower()
        suffix_parts = [engine]

        if engine == "llm":
            # LLMTranslator 会从环境变量读取模型名；这里优先从实例取，兜底读环境变量
            model = getattr(self.__trans, "model", "") or os.getenv("LLM_MODEL_NAME", "")
            suffix_parts.append(self.__sanitize_filename_token(model))

        suffix = ".".join(suffix_parts)
        return src_file.parent / f"{src_file.stem}.{target_lang}.{suffix}{src_file.suffix}"

    def __resolve_target_file(self, src_file: Path, target_lang: str) -> tuple[Path | None, str]:
        """
        决定输出文件策略：
        - 默认：若输出文件存在则跳过（返回 None, "skip"）
        - --continue：沿用“加数字后缀”逻辑生成新文件（返回 ensure_unique_output_path(base), "continue"）
        - --rewrite：覆盖已存在输出文件（返回 base, "rewrite"）
        """
        base = self.__build_target_file(src_file, target_lang)
        continue_mode = bool(getattr(self.__args, "continue_mode", False))
        rewrite = bool(getattr(self.__args, "rewrite", False))

        if continue_mode:
            return ensure_unique_output_path(base), "continue"
        if rewrite:
            return base, "rewrite"
        if base.exists():
            return None, "skip"
        return base, "write"

    @staticmethod
    def __generate_nodes(src_lines: list[str]) -> list[Node]:
        """
        扫描每行，依次为每行生成节点
        """
        is_front_matter = False
        # 在```包裹的代码块中
        is_code_block = False
        # 忽略翻译的部分，实际上和代码块内容差不多，只是连标识符都忽略了
        is_not_trans = False
        is_insert_warnings = config.insert_warnings
        nodes = []
        for line in src_lines:
            if line.strip() == "---":
                is_front_matter = not is_front_matter
                nodes.append(TransparentNode(line))
                # 添加头部的机器翻译警告的占位符
                if not is_front_matter and is_insert_warnings:
                    nodes.append(TransparentNode("___HOLD_To_FILL_WARNING___"))
                    is_insert_warnings = False
                continue

            if line.startswith("```"):
                is_code_block = not is_code_block
                nodes.append(TransparentNode(line))
                continue

            if line.startswith("__do_not_translate__"):
                is_not_trans = not is_not_trans
                continue

            # 处理front matter
            if is_front_matter:
                if line.startswith(tuple(config.front_matter_key_value_keys)):
                    nodes.append(KeyValueNode(line))
                elif line.startswith(tuple(config.front_matter_transparent_keys)):
                    nodes.append(TransparentNode(line))
                elif line.startswith(tuple(config.front_matter_key_value_array_keys)):
                    nodes.append(KeyValueArrayNode(line))
                else:
                    nodes.append(SolidNode(line))

            # 处理代码块
            elif is_code_block or is_not_trans:
                nodes.append(TransparentNode(line))

            else:
                # 空行或者图片、音频等不需要翻译的内容
                if len(line.strip()) == 0 or line.startswith(("<audio", "<img ")):
                    nodes.append(TransparentNode(line))
                # 图片或链接
                elif Patterns.ImageOrLink.search(line):
                    nodes.append(ImageOrLinkNode(line))
                elif line.strip().startswith("#") and " " in line.strip():  # 标题（必须含空格，如 "# Title"）
                    nodes.append(TitleNode(line))
                    # 一级标题
                    if line.strip().startswith("# ") and is_insert_warnings:
                        nodes.append(TransparentNode("___HOLD_To_FILL_WARNING___"))
                        is_insert_warnings = False
                elif line.strip().startswith("#"):  # 仅 "#" / "##" 无空格无标题文字，原样保留
                    nodes.append(TransparentNode(line))
                else:  # 普通文字
                    nodes.append(SolidNode(line))
        return nodes

    def __translate_lines(self, raw_data: RawData, src_lang: str, target_lang: str, pbar: Pbar) -> str:
        """
        执行数据的拆分翻译组装
        """
        # 待翻译md文本
        translated_lines = self.__trans.translate_in_batch(raw_data, src_lang, target_lang, pbar).splitlines()

        # 将翻译后的内容填充到节点中
        start_pos = 0
        nodes = copy.deepcopy(raw_data.nodes)
        for node in nodes:
            if node.trans_lines == 0:
                # 若有机器翻译警告的占位符，则填充警告内容
                if isinstance(node, TransparentNode) and node.value == "___HOLD_To_FILL_WARNING___":
                    node.value = f"\n> {config.warnings_mapping.get(target_lang, 'Warning Not Found')}\n"
                continue
            elif node.trans_lines == 1:
                node.value = translated_lines[start_pos]
            else:
                node.value = "\n".join(translated_lines[start_pos: start_pos + node.trans_lines])
            start_pos += node.trans_lines

        return "".join(node.compose() for node in nodes)

    def __preprocessing(self, src_file: Path) -> RawData:
        """
        预处理，读取文件，生成节点，将待翻译文本分块
        :param src_file:
        :return:
        """
        src_lines = src_file.read_text(encoding="utf-8").splitlines()
        # 生成节点
        nodes = self.__generate_nodes(src_lines)

        # 待翻译文本
        lines_to_translate = "".join(node.get_trans_buff() for node in nodes if node.get_trans_buff()).splitlines()
        # 将待翻译文本中的空行取出
        empty_line_position = [position for position, line in enumerate(lines_to_translate) if not line.strip()]
        lines_to_translate = [line for line in lines_to_translate if line.strip()]

        # 将文本分成多个文本块，避免单次请求过长
        chunk_size = int(getattr(config, "chunk_size_chars", 500) or 500)
        chunk_size = max(1, chunk_size)

        # 仅在 LLM 模式下启用“上下文窗口”；上下文只用于理解，不参与回填
        before_n = int(getattr(config, "llm_context_before_lines", 0) or 0)
        after_n = int(getattr(config, "llm_context_after_lines", 0) or 0)
        before_n = max(0, before_n)
        after_n = max(0, after_n)
        use_llm_context = (config.translator or "").lower() == "llm" and (before_n > 0 or after_n > 0)

        # 先计算 chunk 的行区间（start, end）
        spans: list[tuple[int, int]] = []
        start, length = 0, 0
        for idx, line in enumerate(lines_to_translate):
            if length == 0:
                start = idx
            length += len(line)
            if length > chunk_size:
                spans.append((start, idx + 1))
                length = 0
        if length and lines_to_translate:
            spans.append((start, len(lines_to_translate)))

        chunks = []
        for s, e in spans:
            body_lines = lines_to_translate[s:e]
            skipped_parts, need_translate_parts, parts_count = self.__handle_chunk('\n'.join(body_lines) + '\n')

            if use_llm_context:
                context_before_lines = lines_to_translate[max(0, s - before_n):s]
                context_after_lines = lines_to_translate[e:min(len(lines_to_translate), e + after_n)]
                context_before = "\n".join(context_before_lines)
                context_after = "\n".join(context_after_lines)
                chunks.append((context_before, skipped_parts, need_translate_parts, parts_count, context_after))
            else:
                chunks.append((skipped_parts, need_translate_parts, parts_count))

        # 统计需要翻译的字符数（仅统计“正文”而不包含上下文）
        if use_llm_context:
            chars_count = sum(len("\n".join(need.values())) for _, _, need, _, _ in chunks)
        else:
            chars_count = sum(len("\n".join(need.values())) for _, need, _ in chunks)

        return RawData(nodes, chunks, empty_line_position, chars_count)

    @staticmethod
    def __handle_chunk(chunk: str) -> tuple[dict[int, str], dict[int, str], int]:
        """
        按文本块进行处理，将文本块分为跳过的部分和需要翻译的部分
        :param chunk: 文本块
        :return:
        """
        parts: list[str] = Patterns.Skipped.split(chunk)
        # 跳过的部分
        skipped_parts: dict[int, str] = {}
        # 需要翻译的部分
        need_translate_parts: dict[int, str] = {}
        position = 0
        for part in parts:
            if len(part) == 0:
                continue
            if Patterns.Skipped.search(part):
                skipped_parts.update({position: part})
            else:
                need_translate_parts.update({position: part})
            position += 1
        # 组装翻译
        return skipped_parts, need_translate_parts, position

    def __translate_to(self, src_file: Path, target_lang: str, target_file: Path, global_pbar: tqdm, raw_data: RawData) -> None:
        """
        执行文件的读取、翻译、写入
        """
        logging.info(f"Translating {shortedPath(src_file)} to {target_lang}")

        # 初始化当前线程的进度条
        local_pbar = tqdm(total=raw_data.chars_count, desc=shortedPath(target_file), unit='Chars',
                          unit_scale=True, leave=False, unit_divisor=1000)
        pbar = Pbar(global_pbar, local_pbar)
        try:
            translated_text = self.__translate_lines(raw_data, config.src_language, target_lang, pbar)

            markdown_result, last_char = [], ""
            for translated_line in translated_text.splitlines():
                # 空行或者紧凑型语言则直接添加到结果中
                if (not translated_line.strip()) or target_lang in config.compact_langs:
                    markdown_result.append(translated_line)
                    continue
                # 非紧凑型语言则需要在特定的位置添加空格
                parts = Patterns.Expands.split(translated_line)
                line = "".join(expand_part(part, parts, position, last_char) for position, part in enumerate(parts))
                last_char = parts[-1][-1] if parts[-1] else last_char
                markdown_result.append(line)

            target_file.write_text('\n'.join(markdown_result), encoding="utf-8")
            logging.info(f"{shortedPath(src_file)} -> {target_lang} completed.")
            pbar.local_pbar_finished()
        except Exception as e:
            logging.error(f"Error occurred when translating {shortedPath(src_file)} to {target_lang}: {e}")
            pbar.local_pbar_finished(is_fail=True)
            # 重新抛出异常，让主线程捕获
            raise e

    def __collect_files_to_translate(self, folders: list[str]) -> list[tuple[Path, list[str]]]:
        """
        按传入的文件夹列表收集需要翻译的文档和目标语言
        :param folders: 文件夹列表
        :return:
        """
        files_to_translate = []
        for folder in folders:
            folder = Path(folder)
            if not folder.exists():
                logging.warning(f"{folder} does not exist, Skipped!!!")
                continue
            if folder.is_file():
                config.src_filenames = [folder.stem]
                folder = folder.parent

            # 每个文件夹下至少存在一个配置中的文件名
            if not any((Path(folder) / f"{src_filename}.md").exists() for src_filename in config.src_filenames):
                logging.warning(f"{folder} does not contain any file in src_filenames, Skipped!")
                continue

            for src_filename in config.src_filenames:
                src_file = Path(folder) / (src_filename + '.md')
                if not src_file.exists():
                    continue
                # 将要被翻译至的语言
                target_langs: list[str] = []
                for lang in config.target_langs:
                    target_langs.append(lang)
                if len(target_langs):
                    files_to_translate.append((src_file, target_langs))
        return files_to_translate

    def __parallel_translate(self, files_to_translate: list[tuple[Path, list[str]]]) -> None:
        """
        多线程翻译
        """
        # 先按输出策略过滤“真正需要翻译的任务”
        jobs_by_file: dict[Path, list[tuple[str, Path]]] = {}
        for src_file, target_langs in files_to_translate:
            for target_lang in target_langs:
                target_file, action = self.__resolve_target_file(src_file, target_lang)
                if action == "skip":
                    logging.info(f"Skip (output exists): {shortedPath(self.__build_target_file(src_file, target_lang))}")
                    continue
                if target_file is None:
                    continue
                jobs_by_file.setdefault(src_file, []).append((target_lang, target_file))

        files_raw_data: dict[Path, RawData] = {}
        total_chars_count = 0
        for src_file, jobs in jobs_by_file.items():
            # 先做预处理
            try:
                raw_data = self.__preprocessing(src_file)
                total_chars_count += raw_data.chars_count * len(jobs)
                files_raw_data[src_file] = raw_data
            except Exception as e:
                logging.error(f"Error occurred when preprocessing {src_file.name}: {e}")
                continue

        if len(files_raw_data) == 0:
            logging.warning("No files to translate, exit!")
            return

        # 设置线程数
        threads = config.threads
        if threads <= 0:
            threads = len(config.target_langs)
        if threads > 30:
            threads = 30

        futures = []
        # 初始化全局进度条
        global_pbar = tqdm(total=total_chars_count, desc='Total', unit='Chars', unit_scale=True, colour='#01579B',
                           unit_divisor=1000)
        # 初始化线程池
        executor = concurrent.futures.ThreadPoolExecutor(thread_name_prefix='Translator', max_workers=threads)
        # 将logging输出重定向到tqdm
        with logging_redirect_tqdm():
            for src_file, jobs in jobs_by_file.items():
                if (raw_data := files_raw_data.get(src_file)) is None:
                    continue
                logging.info(
                    f"{shortedPath(src_file)} -> chars count: {get_size(raw_data.chars_count, factor=1000, suffix='')}")
                futures.extend([
                    executor.submit(self.__translate_to, src_file, target_lang, target_file, global_pbar, raw_data)
                    for target_lang, target_file in jobs
                ])

            # 清空不再使用的数据
            files_raw_data.clear()
            # 等待所有线程结束
            concurrent.futures.wait(futures)

        # 检查有无异常
        global_pbar.colour = '#F44336' if any(future.exception() is not None for future in futures) else '#98c379'
        global_pbar.close()

    def main(self):
        # 未传入参数则让用户输入
        if (folders := self.__args.f) is None:
            folders = [input("Please input the markdown document location: ")]

        # 按传入的参数收集需要翻译的文档和目标语言
        files_to_translate = self.__collect_files_to_translate(folders)
        if len(files_to_translate):
            logging.info(f"Current translator engine is: {config.translator}")
            continue_mode = bool(getattr(self.__args, "continue_mode", False))
            rewrite = bool(getattr(self.__args, "rewrite", False))
            if continue_mode:
                logging.info("Output mode: continue (generate new file with numeric suffix if exists)")
            elif rewrite:
                logging.info("Output mode: rewrite (overwrite existing output file)")
            else:
                logging.info("Output mode: default (skip if output file exists)")
            
            # 打印预期的输入和输出文件及语言类型
            logging.info("=" * 80)
            logging.info("Translation Plan:")
            logging.info(f"Source Language: {config.src_language}")
            logging.info(f"Target Languages: {', '.join(str(lang) for lang in config.target_langs)}")
            logging.info("=" * 80)
            for src_file, target_langs in files_to_translate:
                logging.info(f"Input:  {shortedPath(src_file)} (Language: {config.src_language})")
                for target_lang in target_langs:
                    target_file, action = self.__resolve_target_file(src_file, target_lang)
                    if action == "skip":
                        logging.info(f"Output: {shortedPath(self.__build_target_file(src_file, target_lang))} (Language: {target_lang}) [SKIP: exists]")
                    else:
                        # action: write / continue / rewrite
                        suffix = "" if action == "write" else (" [CONTINUE]" if action == "continue" else " [REWRITE]")
                        logging.info(f"Output: {shortedPath(target_file)} (Language: {target_lang}){suffix}")
                logging.info("-" * 80)
            logging.info("=" * 80)
            
            self.__parallel_translate(files_to_translate)
        else:
            logging.warning("No files to translate, exit!")


if __name__ == "__main__":
    translater = MdTranslater(get_arguments())
    translater.main()
