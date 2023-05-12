import hashlib
import codecs
import datetime
import glob
import json
import os
import re
import ssl
import sys
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
        self.url = 'https://translate.google.com.hk/translate_a/single'
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


class Node:
    def __init__(self):
        self.signs = ''
        self.value = ''
        self.trans_lines = 1

    def get_trans_buff(self):
        if self.trans_lines:
            return self.value + '\n'
        return None

    def compose(self):
        return self.value


# 内容无需翻译
class TransparentNode(Node):
    def __init__(self, line):
        super().__init__()
        self.value = line
        self.trans_lines = 0


# 内容全部需翻译
# 比如MD中的正文文本块
class SolidNode(Node):
    def __init__(self, line):
        super().__init__()
        self.value = line[0:-1]


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


class KeyValueNode(Node):
    def __init__(self, line):
        super().__init__()
        idx = line.index(':')
        self.signs = line[0: idx + 1]
        self.value = line[idx + 1:].strip()

    def compose(self):
        return self.signs + ' ' + self.value


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


class TitleNode(Node):
    def __init__(self, line):
        super().__init__()
        idx = line.index(' ')
        self.signs = line[0: idx]
        self.value = line[idx + 1:-1]
        print(self.value)

    def compose(self):
        return self.signs + " " + self.value


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


class ImageNode(Node):
    def __init__(self, line):
        super().__init__()
        idx1 = line.index('[')
        idx2 = line.index(']')
        if idx1 == idx2 - 1:
            self.trans_lines = 0
            self.value = line
        else:
            lstr = line[0: idx1 + 1]
            mstr = line[idx1 + 1: idx2]
            rstr = line[idx2: -1]
            self.value = mstr
            self.signs = []
            self.signs.append(lstr)
            self.signs.append(rstr)

    def compose(self):
        if self.trans_lines == 0:
            return self.value
        return self.value.join(self.signs)


class LinkNode(Node):
    def __init__(self, line):
        super().__init__()
        pattern = r'\[.*?\]\(.*?\)'
        p = re.compile(pattern)
        text = p.split(line)
        links = re.findall(pattern, line)
        tips = []
        self.signs = []
        for link in links:
            idx = link.index(']')
            tips.append(link[1:idx])
            self.signs.append(link[idx + 2:-2])
        self.text_num = len(text)
        self.link_num = len(links)
        self.trans_lines = self.text_num + self.link_num
        self.value = '\n'.join(text + tips)
        # print(self.value)
        # print(tips)
        # print(self.signs)

    def compose(self):
        self.value = self.value.split('\n')
        text = self.value[0:self.text_num]
        tips = self.value[self.text_num:-1]
        links = []
        for i in range(0, self.link_num):
            link = f'[{tips[i]}]({self.signs[i]})'
            links.append(link)
        results = []
        for i in range(0, self.link_num):
            results.append(text[i])
            results.append(links[i])
        results.append(text[-1])
        return ''.join(results)


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


class KeyValueArrayNode(Node):
    def __init__(self, line):
        super().__init__()
        idx = line.index(':')
        key = line[0: idx + 1]
        self.signs = key
        value = line[idx + 1:].strip()
        if value.startswith('['):
            items = value[2:-2].split('", "')
            self.value = '\n'.join(items)
            self.trans_lines = len(items)
        else:
            print("Wrong format with MdTransItemKeyValueArray:", text)

    def compose(self):
        items = self.value.split('\n')
        return "{} [{}]".format(self.signs, '\",\"'.join(items))


class MdTranslater():
    langs = ['en', 'zh-tw', 'th', 'hi', 'ms', 'tl', 'id', 'vi']

    def check_missing(self, md_folder):
        for lang in self.langs:
            dest_filename = md_folder + '/index.' + lang + '.md'
            if not os.path.exists(dest_filename):
                print('lack ', dest_filename)

    def translate(self, lines, src_lang, dest_lang):
        tmp = ""
        translated_text = ""
        for line in lines:
            tmp = tmp + line + '\n'
            if len(tmp) > 500:  # 不同语言这个值不同
                translated_text += GoogleTrans().translate(tmp, src_lang, dest_lang) + '\n'
                tmp = ""
        if len(tmp) > 0:
            translated_text += GoogleTrans().translate(tmp, src_lang, dest_lang) + '\n'
        return translated_text

    def get_nodes(self, src_lines):
        is_front_matter = False
        is_code_block = False
        nodes = []
        for i in range(len(src_lines)):
            line = src_lines[i]
            if line.strip() == '---':
                is_front_matter = not is_front_matter
                nodes.append(TransparentNode(line))
                if not is_front_matter:
                    nodes.append(TransparentNode(
                        '> Warning: This page was generated by machine translation, please pay attention to the accuracy of the identification information!'))
                continue
            if line.startswith('```'):
                is_code_block = not is_code_block
                nodes.append(TransparentNode(line))
                continue

            if is_front_matter:
                if line.startswith(('title:', 'description:')):
                    nodes.append(KeyValueNode(line))
                elif line.startswith(('date:', 'slug:', 'toc', 'image')):
                    nodes.append(TransparentNode(line))
                elif line.startswith(('tags:', 'categories:', 'keywords:')):
                    nodes.append(KeyValueArrayNode(line))
                else:
                    nodes.append(SolidNode(line))
            elif is_code_block:
                nodes.append(TransparentNode(line))
            else:
                if len(line.strip()) == 0:  # 空行
                    nodes.append(TransparentNode(line))
                elif re.search('!\[.*?\]\(.*?\)', line) is not None:  # 图片
                    nodes.append(ImageNode(line))
                    # nodes.append(MdTransItemReserve(line))
                elif re.search('\[.*?\]\(.*?\)', line) is not None:
                    nodes.append(LinkNode(line))
                elif line.strip().startswith('#'):  # 标题
                    nodes.append(TitleNode(line))
                elif line.startswith('<audio') or line.startswith('<img '):
                    nodes.append(TransparentNode(line))
                else:  # 普通文字
                    nodes.append(SolidNode(line))
        return nodes

    def translate_md(self, src_lines, src_lang, dest_lang):
        nodes = self.get_nodes(src_lines)
        # 待翻译md文本
        src_md_text = 'BEGIN\n'
        for node in nodes:
            trans_buff = node.get_trans_buff()
            if trans_buff:
                src_md_text += trans_buff
        src_md_text += 'END'
        print(src_md_text)
        # sys.exit(0)
        # return
        # 分割文本，每次翻译，发送大小不大于2000
        src_lines = src_md_text.splitlines()
        translated_text = self.translate(src_lines, src_lang, dest_lang)
        #
#         translated_text = '''Begin
# "Windows configuration is the problem that the Ubuntu is not effective"
# ""
# technology
# Operation and maintenance
# SSH
# Ubuntu
# Operation and maintenance
# SSH
# Ubuntu
# Windows configuration is free to entertain Ubuntu without taking effect
#
# cause
#
# During the configuration of my personal blog, I plan to use GitHub Action to automatically deploy, which needs to be used to use the SSH key to set aside.
#
# Reference link
#
# 1.
#
#
# How to configure the SSH key to log in at Ubuntu 20.04
# 2.
#
#
# Solution does not take effect after the success of SSH -free login configuration
# Configuration
#
# The blogger uses win10, ubuntu20.04;
#
# The process of configuration key is very simple. First of all
#
# Then use the `ssh-copy -d remote_username@server_ip_address` to deploy the public key to the remote server, but Windows generally does not have a` SSH-Copy-Id` command, so you can use the following command instead.
#
# After that, restart the SSH service, use the `SSH Remote_username@Server_IP_ADDDRESS` Connection to find that the password is still required. After checking the information, the link 2 is on the Linux platform and is not suitable for Windows. Best thought.
#
# Solution
#
# It is found that the OpenSSH AUTHENTINT AGENT item is not started. The description is clear, that is, it is used to verify the public and private key. After the service is turned on, the attempt is still unable to connect again.
# Finally, add config files in your .ssh directory
#
# Re -connect after saving and solve it perfectly!
#
# End
# '''

        translated_lines = translated_text.splitlines()
        print(translated_lines)
        start_pos = 1  # 从第一行开始对应，首行为添加的无意义
        for node in nodes:
            node_trans_lines = node.trans_lines
            if node_trans_lines == 0:

                continue
            elif node_trans_lines == 1:
                node.value = translated_lines[start_pos]
                start_pos += 1
                print("signs: ", node.signs)
                print("value: " + node.value)
            else:
                node.value = '\n'.join(translated_lines[start_pos:start_pos + node_trans_lines])
                start_pos += node_trans_lines

        final_md_text = ''
        for node in nodes:
            final_md_text += node.compose()
        print(final_md_text)
        sys.exit(0)
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
