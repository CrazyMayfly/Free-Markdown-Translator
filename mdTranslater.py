import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import execjs

from cgitb import text

# ssl._create_default_https_context = ssl._create_unverified_context
warnings_mapping = {
    'en': 'Warning: This page is translated by MACHINE, which may lead to POOR QUALITY or INCORRECT INFORMATION, please read with CAUTION!',
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
    'pt': 'Aviso: Este artigo é traduzido por máquina, o que pode levar a má qualidade ou informações incorretas, leia com atenção!'
}

appendix = ['', '.tw', '.hk', '.af', '.ai', '.ag', '.ar', '.au', '.bh', '.bd', '.by', '.bz', '.bo', '.br', '.bn', '.bi',
            '.kh',
            '.co', '.cu', '.cy', '.cz', '.do', '.ec', '.eg', '.sv', '.et', '.fj', '.ge', '.gh', '.gi', '.gr', '.gt',
            '.gy', '.ht', '.iq', '.jm', '.jo', '.kz', '.kw', '.lv', '.lb', '.ly', '.my', '.mt', '.mx', '.mm',
            '.na', '.nr', '.np', '.ni', '.ng', '.nf', '.om', '.pk', '.ps', '.pa', '.pg', '.py', '.pe', '.ph', '.pl',
            '.pt', '.pr', '.qa', '.ru', '.vc', '.sa', '.sl', '.sg', '.sb', '.se', '.tj', '.tn', '.tr', '.tv',
            '.ua', '.uy', '.ve', '.vn', '.vg']

load_balancing_idx = -1
lock = threading.Lock()


def lbi_add_one():
    with lock:
        global load_balancing_idx
        load_balancing_idx += 1
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
        req = urllib.request.Request(url=self.url, headers=self.header)
        page_source = urllib.request.urlopen(req).read().decode("utf-8")
        self.TKK = re.findall(r"tkk:'([0-9]+\.[0-9]+)'", page_source)[0]

    def construct_url(self):
        self.url = f'https://translate.google.com{appendix[self.idx % len(appendix)]}/translate_a/single'

        self.header['referer'] = f'https://translate.google.com{appendix[self.idx % len(appendix)]}'
        print(self.url)
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
        if retries > 5:
            return ''
        try:
            result = self.query(sourceTxt, srcLang, lang_to=targetLang)[2]
            if result is None:
                retries += 1
                print('retry ', retries)
                self.idx = lbi_add_one()
                self.translate(sourceTxt, srcLang, targetLang, retries)
            else:
                return result
        except Exception as e:
            print(e)
            retries += 1
            print(retries)
            self.idx = lbi_add_one()
            self.translate(sourceTxt, srcLang, targetLang, retries)


class Node:
    def __init__(self, line):
        self.signs = ''
        self.value = ''
        # 开头为1. 等情况
        self.index = ''
        self.trans_lines = 1
        self.line = line
        if re.match(r'\d+\. ', line):
            self.index = line[0:3]
            self.line = line[3:]
        elif line.startswith('- '):
            self.index = line[0:2]
            self.line = line[2:]

    def get_trans_buff(self):
        if self.trans_lines:
            return self.value + '\n'
        return None

    def compose(self):
        return self.index + self.value


# 内容无需翻译
class TransparentNode(Node):
    def __init__(self, line):
        super().__init__(line)
        self.value = self.line
        self.trans_lines = 0


# 内容全部需翻译
# 比如MD中的正文文本块
class SolidNode(Node):
    def __init__(self, line):
        super().__init__(line)
        self.value = self.line[0:-1]

    def compose(self):
        return self.index + self.signs + self.value + '\n'


# 内容为#key:value形式，value需要翻译
class KeyValueNode(Node):
    def __init__(self, line):
        super().__init__(line)
        idx = self.line.index(':')
        self.signs = self.line[0: idx + 1]
        self.value = self.line[idx + 1:].strip()

    def compose(self):
        return self.index + self.signs + ' ' + self.value + '\n'


# 内容为### Title形式，Title需要翻译
class TitleNode(Node):
    def __init__(self, line):
        super().__init__(line)
        idx = self.line.index(' ')
        self.signs = self.line[0: idx]
        self.value = self.line[idx + 1:-1]

    def compose(self):
        return self.index + self.signs + " " + self.value + '\n'


# 内容为![图片标题](01.jpg) 形式，图片标题需要翻译
class ImageNode(Node):
    def __init__(self, line):
        super().__init__(line)
        idx1 = self.line.index('[')
        idx2 = self.line.index(']')
        if idx1 == idx2 - 1:
            self.trans_lines = 0
            self.value = self.line
        else:
            lstr = self.line[0: idx1 + 1]
            mstr = self.line[idx1 + 1: idx2]
            rstr = self.line[idx2: -1]
            self.value = mstr
            self.signs = []
            self.signs.append(lstr)
            self.signs.append(rstr)

    def compose(self):
        if self.trans_lines == 0:
            return self.value
        return self.index + self.value.join(self.signs)


class LinkNode(Node):
    def __init__(self, line):
        super().__init__(line)
        pattern = r'\[.*?\]\(.*?\)'
        p = re.compile(pattern)
        text = p.split(self.line[0:-1])
        links = re.findall(pattern, self.line)
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
        return self.index + ''.join(results) + '\n'


# 内容为#key:["values1","values2",..."valueN"]形式，value需要翻译
class KeyValueArrayNode(Node):
    def __init__(self, line):
        super().__init__(line)
        idx = self.line.index(':')
        key = self.line[0: idx + 1]
        self.signs = key
        value = self.line[idx + 1:].strip()
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
        return self.index + '{} ["{}"]'.format(self.signs, '\", \"'.join(items)) + '\n'


class MdTranslater:
    def __init__(self, src_lang, base_dir):
        self.src_lang = src_lang
        self.base_dir = base_dir
        self.src_filename = os.path.join(base_dir, 'index.md')
        self.dest_lang = ''
        self.trans = GoogleTrans()
        # 指定要跳过翻译的字符，分别为加粗符号、在``中的非中文字符，`，换行符
        self.skipped_chars = ["\*\*。?", r'`[^\u4E00-\u9FFF]*?`', '`', r'"[^\u4E00-\u9FFF]*?"', '\n']
        # self.pattern = "|".join(map(re.escape, self.skipped_chars))
        self.pattern = "|".join(self.skipped_chars)

    def skipped_chars_translate(self, text, src_lang, dest_lang):
        parts = re.split(f"({self.pattern})", text)
        # 跳过的部分
        skipped_parts = {}
        # 需要翻译的部分
        translated_parts = {}
        idx = 0
        for part in parts:
            if len(part) == 0:
                continue
            is_translated = True
            for skipped_char in self.skipped_chars:
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

    def translate(self, lines, src_lang, dest_lang):
        tmp = "BEGIN\n"
        translated_text = ""
        for line in lines:
            tmp = tmp + line + '\n'
            if len(tmp) > 500:  # 不同语言这个值不同
                tmp += 'END'
                translated_text += self.skipped_chars_translate(tmp, src_lang, dest_lang)
                tmp = "BEGIN\n"

        if len(tmp) > 0:
            tmp += 'END'
            translated_text += self.skipped_chars_translate(tmp, src_lang, dest_lang)
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
                    nodes.append(TransparentNode(f'\n> {warnings_mapping[self.dest_lang]}\n'))
                continue
            if line.startswith('```'):
                is_code_block = not is_code_block
                nodes.append(TransparentNode(line))
                continue

            if is_front_matter:
                if line.startswith(('title:', 'description:')):
                    nodes.append(KeyValueNode(line))
                elif line.startswith(('date:', 'slug:', 'toc', 'image', 'comments', 'readingTime')):
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
        src_md_text = ''
        for node in nodes:
            trans_buff = node.get_trans_buff()
            if trans_buff:
                src_md_text += trans_buff
        # 分割文本，每次翻译，发送大小不大于2000
        src_lines = src_md_text.splitlines()
        translated_text = self.translate(src_lines, src_lang, dest_lang)
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
