import logging
import re
from cgitb import text


class Node:
    def __init__(self, line):
        # 无需翻译的格式相关内容
        self.signs = ''
        # 需要被翻译的内容
        self.value = ''
        # 开头不需要翻译的内容，如1. , - ,>等
        self.index = ''
        # value的行数，若为0表示无需翻译
        self.trans_lines = 1
        self.line = line
        if re.match(r'\d+\. ', line):
            self.index = line[0:3]
            self.line = line[3:]
        elif line.startswith('- ') or line.startswith('> '):
            self.index = line[0:2]
            self.line = line[2:]

    def get_trans_buff(self):
        # 获取该节点的待翻译内容
        if self.trans_lines:
            return self.value + '\n'
        return None

    def compose(self):
        # 将翻译后的内容组装
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
        return self.index + self.value.join(self.signs) + '\n'


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
            self.signs.append(link[idx + 2:-1])
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
            logging.warning(f"Wrong format with MdTransItemKeyValueArray: {text}")

    def compose(self):
        items = self.value.split('\n')
        return self.index + '{} ["{}"]'.format(self.signs, '\", \"'.join(items)) + '\n'
