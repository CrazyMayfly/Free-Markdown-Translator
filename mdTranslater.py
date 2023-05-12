import hashlib
import codecs
import datetime
import glob
import json
import os
import re
import ssl
import time
import traceback
import urllib.parse
import urllib.request
import execjs

from cgitb import text
from importlib.resources import contents
from sre_constants import RANGE
from typing import TYPE_CHECKING
from unittest.util import strclass
from xml.etree.ElementTree import C14NWriterTarget

ssl._create_default_https_context = ssl._create_unverified_context


class GoogleTrans(object):
    def __init__(self):
        self.url = 'https://transla te.google.com.hk/translate_a/single'
        self.TKK = "434674.96463358"  # 随时都有可能需要更新的TKK值

        self.header = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "cookie": "NID=188=M1p_rBfweeI_Z02d1MOSQ5abYsPfZogDrFjKwIUbmAr584bc9GBZkfDwKQ80cQCQC34zwD4ZYHFMUf4F59aDQLSc79_LcmsAihnW0Rsb1MjlzLNElWihv-8KByeDBblR2V1kjTSC8KnVMe32PNSJBQbvBKvgl4CTfzvaIEgkqss",
            "referer": "https://translate.google.cn/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
            "x-client-data": "CJK2yQEIpLbJAQjEtskBCKmdygEIqKPKAQi5pcoBCLGnygEI4qjKAQjxqcoBCJetygEIza3KAQ==",
        }

        self.data = {
            "client": "webapp",  # 基于网页访问服务器
            "sl": "zh-cn",  # 源语言,auto表示由谷歌自动识别
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

        with open('token.js', 'r', encoding='utf-8') as f:
            self.js_fun = execjs.compile(f.read())

        # 构建完对象以后要同步更新一下TKK值
        # self.update_TKK()

    def update_TKK(self):
        url = "https://translate.google.cn/"
        req = urllib.request.Request(url=url, headers=self.header)
        page_source = urllib.request.urlopen(req).read().decode("utf-8")
        self.TKK = re.findall(r"tkk:'([0-9]+\.[0-9]+)'", page_source)[0]

    def construct_url(self):
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

        # print("翻译前：{}，翻译前code：{}".format(originalText, originalLanguageCode))
        # print("翻译后：{}, 翻译后code：{}".format(targetText, lang_to))
        return originalText, originalLanguageCode, targetText, lang_to

    def translate(self, sourceTxt, srcLang, targetLang, retries=0):
        print('translate ... sourceTxt length=', len(sourceTxt))
        if retries > 1:
            return ''
        try:
            result = self.query(sourceTxt, srcLang, lang_to=targetLang)[2]
            print(result)
            if result is None:
                retries += 1
                print('retry ', retries)
                self.translate(sourceTxt, srcLang, targetLang, retries)
            else:
                return result
        except Exception as e:
            print(e)
            retries += 1
            print(retries)
            self.translate(sourceTxt, srcLang, targetLang, retries)



# 内容无需翻译
# 比如 #date: 2022-04-01
class MdTransItemReserve(object):
    def __init__(self, line):
        self.trans_buff = '\n'
        self.value = line.strip()

    def get_trans_buff(self):
        return self.trans_buff

    def compose(self, translated_lines, start_pos):
        translated_lines[start_pos] = self.value + '\n'
        return translated_lines, 1


# 内容全部需翻译
# 比如MD中的正文文本块
class MdTransItemPlainText(object):
    def __init__(self, line):
        self.trans_buff = line.strip() + '\n'

    def get_trans_buff(self):
        return self.trans_buff

    def compose(self, translated_lines, start_pos):
        pass


# 内容为#key:value形式，value需要翻译
class MdTransItemKeyValue(object):
    def __init__(self, line):
        idx = line.index(':')
        lstr = line[0: idx + 1]
        rstr = line[idx + 1:].strip()
        self.trans_buff = rstr + '\n'
        self.value = lstr.rstrip()

    def get_trans_buff(self):
        return self.trans_buff

    def compose(self, translated_lines, start_pos):
        translated_lines[start_pos] = self.value + ' ' + translated_lines[start_pos].rstrip().replace('"', '').replace(
            ':', ' ') + '\n'


# 内容为### Title形式，Title需要翻译
class MdTransItemTitle(object):
    def __init__(self, line):
        idx = line.index(' ')
        lstr = line[0: idx + 1]
        rstr = line[idx + 1:]
        self.trans_buff = rstr.rstrip() + '\n'
        self.value = lstr.rstrip()

    def get_trans_buff(self):
        return self.trans_buff

    def compose(self, translated_lines, start_pos):
        translated_lines[start_pos] = self.value + ' ' + translated_lines[start_pos].rstrip() + '\n'


# 内容为![图片标题](01.jpg) 形式，图片标题需要翻译
class MdTransItemImg(object):
    def __init__(self, line):
        idx1 = line.index('[')
        idx2 = line.index(']')
        if idx1 == idx2 - 1:
            self.value = line[:-1]
            self.trans_buff = '  \n'
            self.type = 1
        else:
            lstr = line[0: idx1 + 1]
            mstr = line[idx1 + 1: idx2]
            rstr = line[idx2: -1]
            self.trans_buff = mstr + '  \n'
            self.value1 = lstr
            self.value2 = rstr
            self.type = 2

    def get_trans_buff(self):
        return self.trans_buff

    def compose(self, translated_lines, start_pos):
        if self.type == 1:
            translated_lines[start_pos] = self.value + '  \n'
        elif self.type == 2:
            translated_lines[start_pos] = self.value1 + translated_lines[start_pos].rstrip() + self.value2 + '  \n'


# 内容为#key:["values1","values2",..."valueN"]形式，value需要翻译
class MdTransItemKeyValueArray(object):
    def __init__(self, line):
        idx = line.index(':')
        lstr = line[0: idx + 1]
        self.value = lstr
        rstr = line[idx + 1:].strip()
        if rstr.startswith('['):
            self.trans_buff = ''
            items = rstr[2:-2].split('\",\"')
            for item in items:
                self.trans_buff = self.trans_buff + item + '  \n'
            self.item_cnt = len(items)
        else:
            print("Wrong format with MdTransItemKeyValueArray:", text)

    def get_trans_buff(self):
        return self.trans_buff

    def compose(self, translated_lines, start_pos):
        value_text = ''
        for idx in range(start_pos, start_pos + self.item_cnt):
            value_text = value_text + '"' + translated_lines[idx].strip().replace('"', '').rstrip('.').replace(':',
                                                                                                               ' ') + '",'

        translated_lines[start_pos] = self.value + ' [' + value_text[:-1] + ']  \n'

        for idx in range(1, self.item_cnt):
            del translated_lines[start_pos + 1]


class MdTranslater():
    langs = ['en', 'zh-tw', 'th', 'hi', 'ms', 'tl', 'id', 'vi']

    def check_missing(self, md_folder):
        for lang in self.langs:
            dest_filename = md_folder + '/index.' + lang + '.md'
            if not os.path.exists(dest_filename):
                print('lack ', dest_filename)

    def replace_useless_char(self, tstr):
        return tstr

    def translate_md(self, src_lines, src_lang, dest_lang):
        is_front_matter = False
        is_code_block = False
        md_trans_items = []
        for i in range(len(src_lines)):
            line = src_lines[i]
            if line.strip() == '---':
                is_front_matter = not is_front_matter
                md_trans_items.append(MdTransItemReserve(line))
                if not is_front_matter:
                    md_trans_items.append(MdTransItemReserve(
                        '> Warning: This page was generated by machine translation, please pay attention to the accuracy of the identification information!'))
                continue
            if line.startswith('```'):
                is_code_block = not is_code_block
                md_trans_items.append(MdTransItemReserve(line))
                continue

            if is_front_matter:
                if line.startswith(('title:', 'description:')):
                    md_trans_items.append(MdTransItemKeyValue(line))
                elif line.startswith(('date:', 'slug:', 'toc', 'image')):
                    md_trans_items.append(MdTransItemReserve(line))
                elif line.startswith(('tags:', 'categories:', 'keywords:')):
                    md_trans_items.append(MdTransItemKeyValueArray(line))

                else:
                    md_trans_items.append(MdTransItemPlainText(line))
            elif is_code_block:
                md_trans_items.append(MdTransItemReserve(line))
            else:
                if len(line.strip()) == 0:  # 空行
                    md_trans_items.append(MdTransItemReserve(line))
                elif re.match('.*\[.*\]\(.*\)', line) is not None:  # 图片和链接
                    md_trans_items.append(MdTransItemImg(line))
                    # md_trans_items.append(MdTransItemReserve(line))
                elif line.strip().startswith('#'):  # 标题
                    md_trans_items.append(MdTransItemTitle(line))
                elif line.startswith('<audio') or line.startswith('<img '):
                    md_trans_items.append(MdTransItemReserve(line))
                else:  # 普通文字
                    md_trans_items.append(MdTransItemPlainText(line))

        # 待翻译md文本
        src_md_text = 'BEGIN  \n'  ##在首尾都要加入特定行，否则翻译后会首尾的空行去掉，造成翻译前后对应不上
        for mdTransItem in md_trans_items:
            src_md_text = src_md_text + mdTransItem.get_trans_buff()
        src_md_text = src_md_text + 'END  \n'  ##在首尾都要加入特定行，否则翻译后会首尾的空行去掉，造成翻译前后对应不上

        print(src_md_text)
        # return
        # 分割文本，每次翻译，发送大小不大于2000
        part_src_md_text = ""
        dest_md_text = ""
        src_lines = src_md_text.splitlines()
        # print('src_lines:', len(src_lines))
        # print('src_lines:', src_lines)
        for line in src_lines:
            part_src_md_text = part_src_md_text + line + "\n"
            if len(part_src_md_text) > 500:  # 不同语言这个值不同
                dest_md_text = dest_md_text + GoogleTrans().translate(part_src_md_text, src_lang, dest_lang) + "\n"
                part_src_md_text = ""
        if len(part_src_md_text) > 0:
            dest_md_text = dest_md_text + GoogleTrans().translate(part_src_md_text, src_lang, dest_lang) + "\n"

        translated_lines = dest_md_text.splitlines()
        # print(translated_lines)
        start_pos = 1  # 从第一行开始对应，首行为添加的无意义
        for mdTransItem in md_trans_items:
            # print(mdTransItem)
            mdTransItem.compose(translated_lines, start_pos)
            start_pos = start_pos + 1

        final_md_text = ''
        for dline in translated_lines[1: -1]:
            final_md_text = final_md_text + dline.rstrip() + '\n'

        return final_md_text

    def translate_md_folder(self, src_lang, dest_lang, md_folder):
        dest_filename = md_folder + '/index.' + dest_lang + '.md'
        if os.path.exists(dest_filename):
            print('already translated ', dest_filename, ' skip.')
            return

        src_filename = md_folder + '/index.' + src_lang + '.md'
        if not os.path.exists(src_filename):
            print('src file ', src_filename, ' not exist! skip.')
            return

        # black list
        if (md_folder.endswith('000019') and dest_lang == 'my') or \
                (md_folder.endswith('000019') and dest_lang == 'hmn'):
            print(dest_filename, 'in black list, skip!')
            return

        print('translate file ', src_filename, ' to ', dest_filename)
        src_lines = ''
        with open(src_filename, encoding='utf-8') as src_filename_data:
            src_lines = src_filename_data.readlines()

        final_md_text = self.translate_md(src_lines, src_lang, dest_lang)
        # print('final_md_text',final_md_text)
        with open(dest_filename, 'w', encoding='utf-8') as outfile:
            outfile.write(final_md_text)

    def translate_md_folder_with_retries(self, src_lang, dest_lang, md_folder, retries=0):
        # print('translate md with retries=',  retries)
        if retries > 20:
            return
        try:
            return self.translate_md_folder(src_lang, dest_lang, md_folder)
        except Exception as e:
            print(e)
            time.sleep(3)
            retries += 1
            self.translate_md_folder_with_retries(src_lang, dest_lang, md_folder, retries)

    def translate_all_md_folder(self, md_folder):
        print('translate_all_md_folder:', md_folder)
        files = [f for f in glob.glob(md_folder + "/**/index.zh-cn.md", recursive=True)]
        for f in files:
            d = os.path.dirname(f)
            for lang in self.langs:
                self.translate_md_folder_with_retries('zh-cn', lang, d)

    def cleanup(self, md_folder):
        print('cleanup:', md_folder)
        files = [f for f in glob.glob(md_folder + "/**/index.zh-cn.md", recursive=True)]
        for f in files:
            d = os.path.dirname(f)
            for lang in self.langs:
                dest_filename = d + '/index.' + lang + '.md'
                if os.path.exists(dest_filename):
                    print('remove ', dest_filename)
                    # os.remove(dest_filename)


if __name__ == '__main__':
    translater = MdTranslater()
    translater.translate_md_folder("zh", "en", '.')
