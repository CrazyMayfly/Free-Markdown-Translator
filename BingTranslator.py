import functools
import random
import re
import sys
import threading
import time
import warnings
from typing import Tuple, Union, List

import execjs
from lxml import etree
import requests

host_url = 'https://www.bing.com/Translator'
api_url = 'https://www.bing.com/ttranslatev3'
headers = {
    'Referer': host_url,
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 '
                  'Safari/537.36',
}
proxies = None


class TranslatorError(Exception):
    pass


class Tse:
    def __init__(self):
        self.default_session_freq = int(1e3)
        self.default_session_seconds = 1.5e3
        self.auto_pool = ('auto', 'detect', 'auto-detect', 'all')
        self.zh_pool = ('zh', 'zh-CN', 'zh-cn', 'zh-CHS', 'zh-Hans', 'zh-Hans_CN', 'cn', 'chi', 'Chinese')

    @staticmethod
    def time_stat(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            if_show_time_stat = kwargs.get('if_show_time_stat', False)
            show_time_stat_precision = kwargs.get('show_time_stat_precision', 2)
            sleep_seconds = kwargs.get('sleep_seconds', 0)
            if if_show_time_stat and sleep_seconds >= 0:
                t1 = time.time()
                result = func(*args, **kwargs)
                t2 = time.time()
                cost_time = round((t2 - t1 - sleep_seconds), show_time_stat_precision)
                sys.stderr.write(f'TimeSpent(function: {func.__name__[:-4]}): {cost_time}s\n')
                return result
            return func(*args, **kwargs)

        return _wrapper

    @staticmethod
    def get_timestamp() -> int:
        return int(time.time() * 1e3)

    @staticmethod
    def get_uuid() -> str:
        _uuid = ''
        for i in range(8):
            _uuid += hex(int(65536 * (1 + random.random())))[2:][1:]
            if 1 <= i <= 4:
                _uuid += '-'
        return _uuid

    def check_language(self,
                       from_language: str,
                       to_language: str,
                       language_map: dict,
                       output_auto: str = 'auto-detect',
                       output_zh: str = 'zh-Hans',
                       if_check_lang_reverse: bool = True,
                       ) -> Tuple[str, str]:
        from_language = output_auto if from_language in self.auto_pool else from_language
        from_language = output_zh if from_language in self.zh_pool else from_language
        to_language = output_zh if to_language in self.zh_pool else to_language

        if from_language != output_auto and from_language not in language_map:
            raise TranslatorError(
                'Unsupported from_language[{}] in {}.'.format(from_language, sorted(language_map.keys())))
        elif to_language not in language_map and if_check_lang_reverse:
            raise TranslatorError('Unsupported to_language[{}] in {}.'.format(to_language, sorted(language_map.keys())))
        elif from_language != output_auto and to_language not in language_map[from_language]:
            raise TranslatorError('Unsupported translation: from [{0}] to [{1}]!'.format(from_language, to_language))
        elif from_language == to_language:
            raise TranslatorError(f'from_language[{from_language}] and to_language[{to_language}] should not be same.')
        return from_language, to_language

    @staticmethod
    def debug_language_map(func):
        def make_temp_language_map(from_language: str, to_language: str, default_from_language: str) -> dict:
            if from_language == to_language or to_language == 'auto':
                raise TranslatorError

            temp_language_map = {from_language: to_language}
            if from_language != 'auto':
                temp_language_map.update({to_language: from_language})
            elif default_from_language != to_language:
                temp_language_map.update({default_from_language: to_language, to_language: default_from_language})

            return temp_language_map

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            try:
                language_map = func(*args, **kwargs)
                if not language_map:
                    raise TranslatorError
                return language_map
            except Exception as e:
                if kwargs.get('if_print_warning', True):
                    warnings.warn(f'GetLanguageMapError: {str(e)}.\nThe function make_temp_language_map() works.')
                return make_temp_language_map(kwargs.get('from_language'), kwargs.get('to_language'),
                                              kwargs.get('default_from_language'))

        return _wrapper

    @staticmethod
    def check_input_limit(query_text: str, input_limit: int) -> None:
        if len(query_text) > input_limit:
            raise TranslatorError

    @staticmethod
    def check_query(func):
        def check_query_text(query_text: str, if_ignore_empty_query: bool) -> str:
            if not isinstance(query_text, str):
                raise TranslatorError
            query_text = query_text.strip()
            qt_length = len(query_text)
            if qt_length == 0 and not if_ignore_empty_query:
                raise TranslatorError("The `query_text` can't be empty!")
            return query_text

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            if_ignore_empty_query = kwargs.get('if_ignore_empty_query', True)
            query_text = list(args)[1] if len(args) >= 2 else kwargs.get('query_text')
            query_text = check_query_text(query_text, if_ignore_empty_query)
            if not query_text and if_ignore_empty_query:
                return query_text

            if len(args) >= 2:
                new_args = list(args)
                new_args[1] = query_text
                return func(*tuple(new_args), **kwargs)
            return func(*args, **{**kwargs, **{'query_text': query_text}})

        return _wrapper


class Bing(Tse):
    def __init__(self):
        super().__init__()
        self.__begin_time = time.time()
        self.__language_map = None
        self.__session = None
        self.__tk = None
        self.__ig_iid = None
        self.__query_count = 0
        self.__sleep_seconds = 0
        self.__length_limit = 1000
        self.__updated = False
        self.__update_lock = threading.Lock()

    @Tse.debug_language_map
    def get_language_map(self, et) -> dict:
        lang_list = et.xpath('//*[@id="tta_srcsl"]/option/@value') or et.xpath('//*[@id="t_srcAllLang"]/option/@value')
        lang_list = sorted(list(set(lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    @staticmethod
    def get_ig_iid(html: str, et) -> dict:
        iid = et.xpath('//*[@id="tta_outGDCont"]/@data-iid')[0]  # 'translator.5028'
        ig = re.compile('IG:"(.*?)"').findall(html)[0]
        return {'iid': iid, 'ig': ig}

    @staticmethod
    def get_tk(html: str) -> dict:
        result_str = re.compile('var params_AbusePreventionHelper = (.*?);').findall(html)[0]
        result = execjs.eval(result_str)
        return {'key': result[0], 'token': result[1]}

    @staticmethod
    def get_length_limit(et):
        length_limit = et.xpath('//*[@id="t_charCount"]/text()')[0].split('/')[1]
        return int(length_limit)

    @Tse.time_stat
    @Tse.check_query
    def translate(self, query_text: str, from_language: str = 'auto', to_language: str = 'en') -> Union[str, dict]:
        """
        https://bing.com/Translator, https://cn.bing.com/Translator.
        :param query_text: str, must.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :return: str or dict
        """
        print(f'trans {query_text}')
        self.try_update_states()
        from_language, to_language = self.check_language(from_language, to_language, self.__language_map)
        payload = {
            'text': query_text,
            'fromLang': from_language,
            'to': to_language,
            'tryFetchingGenderDebiasedTranslations': 'true'
        }
        payload = {**payload, **self.__tk}
        api_url_param = f'?isVertical=1&&IG={self.__ig_iid["ig"]}&IID={self.__ig_iid["iid"]}'
        r = self.__session.post(api_url + api_url_param, headers=headers, data=payload, proxies=proxies)
        r.raise_for_status()
        if self.__sleep_seconds:
            time.sleep(self.__sleep_seconds)
        self.__query_count += 1

        try:
            data = r.json()
            return data[0]['translations'][0]['text']
        except requests.exceptions.JSONDecodeError:  # 122
            data_html = r.text
            et = etree.HTML(data_html)
            ss = et.xpath('//*/textarea/text()')
            return ss[-1]

    def translate_lines(self, lines: str | List, from_language: str = 'auto', to_language: str = 'en',
                        output_text=False) -> str | List:
        if isinstance(lines, str):
            lines = lines.split('\n')
        # 统计空行的位置并剔除
        empty_line_index = [i for i, line in enumerate(lines) if not line.strip()]
        lines = [line for line in lines if line.strip()]
        lines = self.translate('\n'.join(lines), from_language, to_language).split('\n')
        # 将空行插入回去
        for i in empty_line_index:
            lines.insert(i, '')
        return lines if not output_text else '\n'.join(lines)

    def translate_html(self,
                       html_text: str,
                       from_language: str = 'auto',
                       to_language: str = 'en',
                       ) -> str:
        """
        Translate the displayed content of html without changing the html structure.
        :param html_text: str, must.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :return: str
        """
        pattern = re.compile('>([\\s\\S]*?)<')
        sentence_list = list(set(pattern.findall(html_text)))
        lines = self.translate_lines(sentence_list, from_language, to_language)
        result_dict = {sentence_list[i]: f'>{lines[i]}<' for i in range(len(lines))}
        return pattern.sub(repl=lambda k: result_dict.get(k.group(1), ''), string=html_text)

    def try_update_states(self, force=False):
        self.__updated = False if force else self.__updated
        not_update_cond_freq = self.__query_count < self.default_session_freq
        not_update_cond_time = time.time() - self.__begin_time < self.default_session_seconds
        while not (self.__updated and not_update_cond_freq and not_update_cond_time):
            self._update_states()
            not_update_cond_freq = not_update_cond_time = self.__updated

    def _update_states(self):
        try:
            self.__session = requests.Session()
            html = self.__session.get(host_url, headers=headers, proxies=proxies).text
            et = etree.HTML(html)
            self.__tk = self.get_tk(html)
            self.__ig_iid = self.get_ig_iid(html, et)
            self.__length_limit = self.get_length_limit(et)
            self.__language_map = self.get_language_map(et)
            self.__begin_time = time.time()
            self.__query_count = 0
            self.__updated = self.__session and self.__tk and self.__ig_iid and self.__language_map and self.__length_limit
        except Exception as e:
            warnings.warn(f'UpdateError: {str(e)}.')
            self.__updated = False


if __name__ == '__main__':
    bing = Bing()
    # print(bing.translate("你好，世界！"))
    print(bing.translate_html('''<html>《季姬击鸡记》,<p>还有<b>另一篇文章</b>《施氏食狮史》。</p></html>'''))
