import copy
import logging
import time

import translators as ts
from Utils import SymbolWidthUtil, RawData, Pbar
from config import config

MAX_RETRY = 5


class TranslateError(Exception):
    pass


class Translator:
    def translate(self, source_text: str, src_lang: str, target_lang: str, retries: int = 0) -> str:
        logging.debug(f"Translating {src_lang} to {target_lang}, length={len(source_text)}, retries={retries}")
        if retries >= MAX_RETRY:
            raise TranslateError(f"Translate failed after {MAX_RETRY} retries.")
        try:
            result = ts.translate_text(
                source_text,
                translator=config.translator,
                from_language=src_lang,
                to_language=target_lang,
                if_ignore_limit_of_length=True,
                if_show_time_stat=False,
            )
            if result is None:
                retries += 1
                logging.warning(f"Translate failed, retry {retries}/{MAX_RETRY}")
                return self.translate(source_text, src_lang, target_lang, retries)
            return result
        except Exception as e:
            retries += 1
            logging.error(f"Translate error: {e}, retry {retries}/{MAX_RETRY}")
            # 重试时等待时间递增
            time.sleep(0.2 * pow(2, retries))
            return self.translate(source_text, src_lang, target_lang, retries)

    def __translate_with_skipped_chars(self, chunk: tuple[dict[int, str], dict[int, str], int], src_lang: str,
                                       target_lang: str, pbar: Pbar) -> str:
        """
        翻译时忽略在config.py中配置的正则表达式，翻译后保证格式不变
        :param chunk: 本次翻译的文本块
        :return: 翻译后的文本
        """
        # 跳过的部分和需要翻译的部分以及所有部分的数量
        skipped_parts, need_translate_parts, parts_count = chunk

        text_to_translate = "\n".join(need_translate_parts.values())
        # 确保api接口返回了结果
        while (translated_text := self.translate(text_to_translate, src_lang, target_lang)) is None:
            pass

        pbar.update(len(text_to_translate))
        translated_text = [line.strip(" ") for line in translated_text.splitlines()]
        # 更新翻译部分的内容
        for position, key in enumerate(need_translate_parts.keys()):
            need_translate_parts[key] = translated_text[position]

        if not target_lang.lower().startswith("zh"):
            # 如果是不是中文，则将skipped_parts中的全角符号变为半角符号
            skipped_parts = {key: SymbolWidthUtil.full_to_half(value) for key, value in skipped_parts.items()}

        total_parts = {**skipped_parts, **need_translate_parts}
        return "".join(total_parts[i] for i in range(parts_count))

    def translate_in_batch(self, raw_data: RawData, src_lang: str, target_lang: str, pbar: Pbar) -> str:
        """
        分批次翻译
        """
        translated_text = [self.__translate_with_skipped_chars(chunk, src_lang, target_lang, pbar) for chunk in
                           # 深拷贝，避免修改原始数据
                           copy.deepcopy(raw_data.chunks)]
        lines = ''.join(translated_text).splitlines()
        # 将空行插入回去
        for i in raw_data.empty_line_position:
            lines.insert(i, '')
        return '\n'.join(lines) + '\n'
