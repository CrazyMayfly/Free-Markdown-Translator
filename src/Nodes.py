import logging
from Utils import Patterns


class Node:
    def __init__(self, line: str):
        # 无需翻译的格式相关内容
        self._signs = ''
        # 需要被翻译的内容
        self.value = ''
        # 开头不需要翻译的内容，如1. , - ,>等
        self._index = ''
        # value的行数，若为0表示无需翻译
        self.trans_lines = 1
        self._line = line
        if Patterns.DigitalOrder.search(line):
            self._index = line[0:3]
            self._line = line[3:]
        elif line.startswith('- ') or line.startswith('> '):
            self._index = line[0:2]
            self._line = line[2:]

    def get_trans_buff(self):
        # 获取该节点的待翻译内容
        if self.trans_lines:
            return self.value + '\n'
        return None

    def compose(self):
        # 将翻译后的内容组装
        return self._index + self.value + "\n"


# 内容无需翻译
class TransparentNode(Node):
    def __init__(self, line):
        super().__init__(line)
        self.value = self._line
        self.trans_lines = 0


# 内容全部需翻译
# 比如MD中的正文文本块
class SolidNode(Node):
    def __init__(self, line):
        super().__init__(line)
        self.value = self._line

    def compose(self):
        return self._index + self._signs + self.value + '\n'


# 内容为#key:value形式，value需要翻译
class KeyValueNode(Node):
    def __init__(self, line):
        super().__init__(line)
        idx = self._line.index(':')
        self._signs = self._line[0: idx + 1]
        self.value = self._line[idx + 1:].strip()

    def compose(self):
        return self._index + self._signs + ' ' + self.value + '\n'


# 内容为### Title形式，Title需要翻译
class TitleNode(Node):
    def __init__(self, line):
        super().__init__(line)
        idx = self._line.index(' ')
        self._signs = self._line[0: idx]
        self.value = self._line[idx + 1:]

    def compose(self):
        return self._index + self._signs + " " + self.value + '\n'


class ImageOrLinkNode(Node):
    def __init__(self, line):
        super().__init__(line)

        # 查找所有图片和链接（包括嵌套的图片和链接）
        matches = Patterns.ImageOrLink.findall(line)
        # 除去图片和链接的其他文字
        self.__text_fragments = Patterns.ImageOrLink.split(line)

        self.__descriptions = []
        self.__links = []
        self.__image_nodes = []
        self.__nested_images = []

        for position, item in enumerate(matches):
            # 提取嵌套的图片和描述
            nested_image, description, = Patterns.DescOrNestedImage.findall(item).pop()
            # 提取链接
            link = Patterns.LinkContent.findall(item).pop()

            self.__descriptions.append(description)
            self.__nested_images.append(nested_image)
            self.__links.append(link)
            # 将图片节点标记出来
            if item.startswith('!'):
                self.__image_nodes.append(position)
        # 需要翻译的部分为描述加上非图片或链接的其他文字
        self.value = '\n'.join(self.__descriptions + self.__text_fragments)
        self.trans_lines = len(self.__descriptions + self.__text_fragments)

    def compose(self):
        # 重组图片和链接
        lines = self.value.split('\n')
        images_or_links = []

        for position, description in enumerate(lines[:len(self.__descriptions)]):
            description = description.strip()
            # 描述为空则获取嵌套的图片
            if not description:
                description = self.__nested_images[position]
            if position in self.__image_nodes:
                images_or_links.append(f'![{description}]({self.__links[position]})')
            else:
                images_or_links.append(f'[{description}]({self.__links[position]})')

        text_fragments = lines[len(self.__descriptions):]
        result = []

        for i in range(len(self.__descriptions + self.__text_fragments)):
            if i % 2 == 0:
                result.append(text_fragments.pop(0))
            else:
                result.append(images_or_links.pop(0))

        return self._index + ''.join(result) + '\n'


# 内容为#key:["values1","values2",..."valueN"]形式，value需要翻译
class KeyValueArrayNode(Node):
    def __init__(self, line):
        super().__init__(line)
        idx = self._line.index(':')
        key = self._line[0: idx + 1]
        self._signs = key
        value = self._line[idx + 1:].strip()
        if value.startswith('['):
            items = value[2:-2].split('", "')
            if not items:
                items = value[2:-2].split('","')
            self.value = '\n'.join(items)
            self.trans_lines = len(items)
        else:
            logging.warning(f"Wrong format with MdTransItemKeyValueArray: {value}")

    def compose(self):
        items = self.value.split('\n')
        return self._index + '{} ["{}"]'.format(self._signs, '\", \"'.join(items)) + '\n'
