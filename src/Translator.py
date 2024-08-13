import logging
import translators as ts
from Utils import Patterns
from config import config

MAX_RETRY = 5


class Translator:
    def translate(self, sourceTxt, srcLang, targetLang, retries=0):
        logging.debug(f"Translating {srcLang} to {targetLang}, length={len(sourceTxt)}, retries={retries}")
        if retries >= MAX_RETRY:
            return ""
        try:
            result = ts.translate_text(
                sourceTxt,
                translator=config.translator,
                from_language=srcLang,
                to_language=targetLang,
                if_ignore_limit_of_length=True,
                if_show_time_stat=False,
            )
            if result is None:
                retries += 1
                logging.warning(f"Translate failed, retry {retries}/{MAX_RETRY}")
                return self.translate(sourceTxt, srcLang, targetLang, retries)
            return result
        except Exception as e:
            retries += 1
            logging.error(f"Translate error, retry {retries}/{MAX_RETRY}")
            logging.error(e)
            return self.translate(sourceTxt, srcLang, targetLang, retries)

    def __translate_with_skipped_chars(self, text, src_lang, target_lang):
        """
        翻译时忽略在config.py中配置的正则表达式，翻译后保证格式不变
        :param text: 本次翻译的文本
        :return: 翻译后的文本
        """
        parts = Patterns.Skipped.split(text)
        # 跳过的部分
        skipped_parts = {}
        # 需要翻译的部分
        translated_parts = {}
        idx = 0
        for part in parts:
            if len(part) == 0:
                continue
            if Patterns.Skipped.search(part):
                skipped_parts.update({idx: part})
            else:
                translated_parts.update({idx: part})
            idx += 1

        # 组装翻译
        text = "\n".join(translated_parts.values())
        translate = self.translate(text, src_lang, target_lang)
        # 确保api接口返回了结果
        while translate is None:
            translate = self.translate(text, src_lang, target_lang)

        translated_text = [line.strip(" ") for line in translate.splitlines()]
        # 更新翻译部分的内容
        for position, key in enumerate(translated_parts.keys()):
            translated_parts[key] = translated_text[position]

        total_parts = {**skipped_parts, **translated_parts}
        return "".join(total_parts[i] for i in range(idx))

    def translate_in_batches(self, lines: list[str], src_lang: str, target_lang: str) -> str:
        """
        分批次翻译
        """
        # 统计空行的位置并剔除
        empty_line_index = [i for i, line in enumerate(lines) if not line.strip()]
        lines = [line for line in lines if line.strip()]
        translated_text = ""
        tmp = ""
        for line in lines:
            tmp = tmp + line + "\n"
            # 控制每次发送的数据量
            if len(tmp) > 500:
                translated_text += self.__translate_with_skipped_chars(
                    tmp, src_lang, target_lang
                )
                tmp = ""
        if tmp.strip():
            translated_text += self.__translate_with_skipped_chars(
                tmp, src_lang, target_lang
            )
        lines = translated_text.splitlines()
        # 将空行插入回去
        for i in empty_line_index:
            lines.insert(i, '')
        return '\n'.join(lines) + '\n'
