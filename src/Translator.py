import logging
import re
import translators as ts
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
        translate = self.translate(text, src_lang, target_lang)
        # 确保api接口返回了结果
        while translate is None:
            translate = self.translate(text, src_lang, target_lang)
        translated_text = translate.split("\n")
        # 更新翻译部分的内容
        for position, key in enumerate(translated_parts.keys()):
            translated_parts[key] = translated_text[position]
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

    def translate_in_batches(self, lines, src_lang, target_lang):
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
