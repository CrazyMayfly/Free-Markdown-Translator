import glob
import json
import os
import re
import time
import urllib.parse
import urllib.request
import execjs

from cgitb import text

# ssl._create_default_https_context = ssl._create_unverified_context
warnings_mapping = {
    'en': 'Warning: This article is translated by machine, which may lead to poor quality or incorrect information, please read with caution!',
    'ja': '警告: この記事は機械翻訳されているため、品質が低かったり不正確な情報が含まれる可能性があります。よくお読みください。',
    'zh-tw': "警告：本文由機器翻譯生成，可能導致質量不佳或信息有誤，請謹慎閱讀！",
    # 西班牙语
    'es': 'Advertencia: este artículo está traducido por una máquina, lo que puede dar lugar a una mala calidad o información incorrecta. ¡Lea atentamente!',
    # 俄语
    'ru': 'Предупреждение: Эта статья переведена автоматически, что может привести к некачественной или неверной информации, пожалуйста, внимательно прочитайте!',
    # 法语
    'fr': 'Attention : cet article est traduit par machine, ce qui peut entraîner une mauvaise qualité ou des informations incorrectes, veuillez lire attentivement !',
    # 德语
    'de': 'Achtung: Dieser Artikel wurde maschinell übersetzt, was zu schlechter Qualität oder falschen Informationen führen kann, bitte sorgfältig lesen!',
    # 印地语
    'hi': 'चेतावनी: यह लेख मशीन द्वारा अनुवादित है, जिससे खराब गुणवत्ता या गलत जानकारी हो सकती है, कृपया ध्यान से पढ़ें!',
    # 葡萄牙语
    'pt':'Aviso: Este artigo é traduzido por máquina, o que pode levar a má qualidade ou informações incorretas, leia com atenção!'
}


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
        return originalText, originalLanguageCode, targetText, lang_to

    def translate(self, sourceTxt, srcLang, targetLang, retries=0):
        print('translate ... sourceTxt length=', len(sourceTxt))
        if retries > 1:
            return ''
        try:
            result = self.query(sourceTxt, srcLang, lang_to=targetLang)[2]
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

    def compose(self):
        return self.value + '\n'


# 内容为#key:value形式，value需要翻译
class KeyValueNode(Node):
    def __init__(self, line):
        super().__init__()
        idx = line.index(':')
        self.signs = line[0: idx + 1]
        self.value = line[idx + 1:].strip()

    def compose(self):
        return self.signs + ' ' + self.value + '\n'


# 内容为### Title形式，Title需要翻译
class TitleNode(Node):
    def __init__(self, line):
        super().__init__()
        idx = line.index(' ')
        self.signs = line[0: idx]
        self.value = line[idx + 1:-1]

    def compose(self):
        return self.signs + " " + self.value + '\n'


# 内容为![图片标题](01.jpg) 形式，图片标题需要翻译
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
        text = p.split(line[0:-1])
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

    def compose(self):
        self.value = self.value.split('\n')
        text = self.value[0:self.text_num]
        tips = self.value[self.text_num:]
        links = []
        for i in range(0, self.link_num):
            link = f'[{tips[i]}]({self.signs[i]})'
            links.append(link)
        results = []
        for i in range(0, self.link_num):
            results.append(text[i])
            results.append(links[i])
        results.append(text[-1])
        return ''.join(results) + '\n'


# 内容为#key:["values1","values2",..."valueN"]形式，value需要翻译
class KeyValueArrayNode(Node):
    def __init__(self, line):
        super().__init__()
        idx = line.index(':')
        key = line[0: idx + 1]
        self.signs = key
        value = line[idx + 1:].strip()
        if value.startswith('['):
            items = value[2:-2].split('", "')
            if not items:
                items = value[2:-2].split('","')
            self.value = '\n'.join(items)
            self.trans_lines = len(items)
        else:
            print("Wrong format with MdTransItemKeyValueArray:", text)

    def compose(self):
        items = self.value.split('\n')
        return '{} ["{}"]'.format(self.signs, '\", \"'.join(items)) + '\n'


class MdTranslater:
    def __init__(self, src_lang, base_dir):
        self.src_lang = src_lang
        self.base_dir = base_dir
        self.src_filename = os.path.join(base_dir, 'index.md')
        self.dest_lang = ''

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
                        '> ' + warnings_mapping[self.dest_lang]))
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
        self.dest_lang = dest_lang
        nodes = self.get_nodes(src_lines)
        # 待翻译md文本
        src_md_text = 'BEGIN\n'
        for node in nodes:
            trans_buff = node.get_trans_buff()
            if trans_buff:
                src_md_text += trans_buff
        src_md_text += 'END'
        # 分割文本，每次翻译，发送大小不大于2000
        src_lines = src_md_text.splitlines()
        translated_text = self.translate(src_lines, src_lang, dest_lang)
        translated_lines = translated_text.splitlines()
        start_pos = 1  # 从第一行开始对应，首行为添加的无意义
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
        dest_filename = os.path.join(self.base_dir, f'index.{dest_lang}.md')
        if os.path.exists(dest_filename):
            if input(f'{dest_filename} already exists, whether to continue(y/n): ') != 'y':
                return
        if not os.path.exists(self.src_filename):
            print('src file ', self.src_filename, ' not exist! skip.')
            return
        print('translate file ', self.src_filename, ' to ', dest_filename)
        with open(self.src_filename, encoding='utf-8') as src_filename_data:
            src_lines = src_filename_data.readlines()
        final_md_text = self.translate_md(src_lines, self.src_lang, dest_lang)
        with open(dest_filename, 'w', encoding='utf-8') as outfile:
            outfile.write(final_md_text)

    def translate_md_folder_with_retries(self, src_lang, dest_lang, md_folder, retries=0):
        if retries > 20:
            return
        try:
            return self.translate_to(src_lang, dest_lang, md_folder)
        except Exception as e:
            print(e)
            time.sleep(3)
            retries += 1
            self.translate_md_folder_with_retries(src_lang, dest_lang, md_folder, retries)


if __name__ == '__main__':
    base_dir = input('Please input the folder: ')
    src_filename = os.path.join(base_dir, 'index.md')
    while not os.path.exists(src_filename):
        base_dir = input(f'Can not find {src_filename}, please enter the valid folder again: ')
        src_filename = os.path.join(base_dir, 'index.en.md')
    translater = MdTranslater('zh', base_dir)
    dest_langs = ['zh-tw', 'en', 'ja']
    for lang in dest_langs:
        translater.translate_to(lang)
