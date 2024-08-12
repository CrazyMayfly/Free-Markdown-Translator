import json
import os
import re
import sys
import threading
import urllib.parse
import urllib.request

# pip install PyExecJS
import execjs

from config import src_language

# Google Translate Api 池
appendix = ['', '.tw', '.hk', '.af', '.ai', '.ag', '.ar', '.au', '.bh', '.bd', '.by', '.bz', '.bo', '.br', '.bn', '.bi',
            '.kh', '.co', '.cu', '.cy', '.cz', '.do', '.ec', '.eg', '.sv', '.et', '.fj', '.ge', '.gh', '.gi', '.gr',
            '.gt', '.gy', '.ht', '.iq', '.jm', '.jo', '.kz', '.kw', '.lv', '.lb', '.ly', '.my', '.mt', '.mx', '.mm',
            '.na', '.nr', '.np', '.ni', '.ng', '.nf', '.om', '.pk', '.ps', '.pa', '.pg', '.py', '.pe', '.ph', '.pl',
            '.pt', '.pr', '.qa', '.ru', '.vc', '.sa', '.sl', '.sg', '.sb', '.se', '.tj', '.tn', '.tr', '.tv',
            '.ua', '.uy', '.ve', '.vn', '.vg']

# 用于负载均衡，当GoogleTrans对象实例化时或者请求出问题、没有返回数据自动切换url
load_balancing_idx = -1

# 应对多线程的锁，为单线程应用时无需加锁
lock = threading.Lock()
logging_lock = threading.Lock()


def lbi_add_one():
    with lock:
        global load_balancing_idx
        load_balancing_idx += 1
        # with logging_lock:
        #     print(f'Current url is https://translate.google.com{appendix[load_balancing_idx % len(appendix)]}')
        return load_balancing_idx


class GoogleTrans(object):
    def __init__(self):
        self.url = 'https://translate.google.com/translate_a/single'
        self.TKK = "434674.96463358"  # 随时都有可能需要更新的TKK值
        self.idx = lbi_add_one()
        self.header = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "cookie": "NID=188=M1p_rBfweeI_Z02d1MOSQ5abYsPfZogDrFjKwIUbmAr584bc9GBZkfDwKQ80cQCQC34zwD4ZYHFMUf4F59aDQLSc79_LcmsAihnW0Rsb1MjlzLNElWihv-8KByeDBblR2V1kjTSC8KnVMe32PNSJBQbvBKvgl4CTfzvaIEgkqss",
            "referer": "https://translate.google.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
            "x-client-data": "CJK2yQEIpLbJAQjEtskBCKmdygEIqKPKAQi5pcoBCLGnygEI4qjKAQjxqcoBCJetygEIza3KAQ==",
        }

        self.data = {
            "client": "webapp",  # 基于网页访问服务器
            "sl": src_language,  # 源语言, auto表示由谷歌自动识别
            "tl": "en",  # 翻译的目标语言
            "hl": "zh-cn",  # 界面语言选中文，毕竟URL都是cn后缀了，就不装美国人了
            # dt表示要求服务器返回的数据类型
            "dt": ["at", "bd", "ex", "ld", "md", "qca", "rw", "rm", "ss", "t"],
            "otf": "2",
            "ssel": "0",
            "tsel": "0",
            "kc": "1",
            "tk": "",  # 谷歌服务器会核对的token
            "q": ""  # 待翻译的字符串
        }

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(os.path.dirname(__file__))
        with open(os.path.join(base_path, 'token.js'), 'r', encoding='utf-8') as f:
            self.js_fun = execjs.compile(f.read())

        # 构建完对象以后要同步更新一下TKK值
        # self.update_TKK()

    def update_TKK(self):
        req = urllib.request.Request(url=self.url, headers=self.header)
        page_source = urllib.request.urlopen(req).read().decode("utf-8")
        self.TKK = re.findall(r"tkk:'([0-9]+\.[0-9]+)'", page_source)[0]

    def construct_url(self):
        # 构建Url时使用负载均衡
        self.url = f'https://translate.google.com{appendix[self.idx % len(appendix)]}/translate_a/single'
        self.header['referer'] = f'https://translate.google.com{appendix[self.idx % len(appendix)]}'
        base = self.url + '?'
        for key in self.data:
            if isinstance(self.data[key], list):
                base = base + "dt=" + "&dt=".join(self.data[key]) + "&"
            else:
                base = base + key + '=' + self.data[key] + '&'
        base = base[:-1]
        return base

    def query(self, q, lang_from='zh-cn', lang_to=''):
        self.data['q'] = urllib.parse.quote(q)
        self.data['tk'] = self.js_fun.call('wo', q, self.TKK)
        self.data['sl'] = lang_from
        self.data['tl'] = lang_to
        url = self.construct_url()
        req = urllib.request.Request(url=url, headers=self.header)
        res = urllib.request.urlopen(req).read().decode("utf-8")
        response = json.loads(res)
        originalLanguageCode = response[2]
        targetText = ""
        originalText = ""
        for ds in response[0]:
            if ds[0]:
                targetText = targetText + ds[0]
            if ds[1]:
                originalText = originalText + ds[1]
        return originalText, originalLanguageCode, targetText, lang_to

    def translate(self, sourceTxt, srcLang, targetLang, retries=0):
        with logging_lock:
            print(
                f'{threading.current_thread().name} is translating {srcLang} to {targetLang}, length={len(sourceTxt)}')
        if retries > 5:
            return ''
        try:
            result = self.query(sourceTxt, srcLang, lang_to=targetLang)[2]
            if result is None:
                retries += 1
                print('retry ', retries)
                # 返回结果为None时切换url
                self.idx = lbi_add_one()
                self.translate(sourceTxt, srcLang, targetLang, retries)
            else:
                return result
        except Exception as e:
            print(e)
            retries += 1
            print('retry ', retries)
            # 出错时切换Url
            self.idx = lbi_add_one()
            self.translate(sourceTxt, srcLang, targetLang, retries)
