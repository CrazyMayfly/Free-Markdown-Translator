# Free Markdown Translator

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![made-with-javascript](https://img.shields.io/badge/Made%20with-JavaScript-1f425f.svg)](https://www.javascript.com)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

## 简介

Free Markdown Translator是一款基于Google Translate API 的免费、开源的Markdown文档（以下简称md）翻译器，能够将你的md翻译成任意种语言。

功能：

- 将md翻译成任意种语言
- 不会破坏md原有的格式，同时支持自定义翻译规则
- 支持多线程翻译，同时加入了负载均衡机制，能够有效地利用谷歌翻译接口并且避免文档翻译失败的发生
- 支持一次程序运行翻译多个文件夹、一个文件夹下的多个文件，增加了便捷性
- 支持在机器翻译的md中添加警告语

Google Translate API参考[VictorZhang2014/free-google-translate: Free Google Translator API 免费的Google翻译 (github.com)](https://github.com/VictorZhang2014/free-google-translate)，本程序参考[如何使用translate.google.cn免費Google翻譯網站翻譯整篇Markdown文檔, V2修改版 (knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## 安装与运行

1. 将仓库克隆或将源代码下载到本地

```bash
git clone git@github.com:AprilInJuly/Free-Markdown-Translator.git
```

2. 安装软件包`PyExecJS`

```bash
pip install PyExecJS
```

3. 进入代码目录，运行代码

```bash
python.exe .\MarkdownTranslator.py
```

### 用法

```bash
python.exe MarkdownTranslator.py [-h] folder [folder ...]
```

参数位置放置待翻译的文件夹，可以添加多个文件夹，程序会自动按顺序翻译每个文件夹下的每个在配置文件中指定的文件。

例如，若指定的目标语言为英语(en)、日本语(ja)，则`readme.md`文件会被翻译到同文件夹下的`readme.en.md`,`readme.ja.md`。

## 配置

请在`config.py`中进行配置

1. `insert_warnings`: 控制是否在文章前面添加机器翻译的Warning
2. `src_language`: 指定源语言，auto表示由谷歌自动识别
3. `warnings_mapping`: 配置目标语言的warning
4. `dest_langs`: 配置目标语言，可以手动指定目标语言，也可以直接使用`warnings_mapping`中配置的目标语言，按照定义顺序翻译
5. `skipped_regexs`: 指定要跳过翻译的字符的正则表达式
6. `detect_filenames`: 文件目录下需要翻译的md文档的名称
7. `front_matter_transparent_keys`: markdown的Front Matter中不用翻译的部分
8. `front_matter_key_value_keys`: Front Matter中需要以Key-Value形式翻译的部分
9. `front_matter_key_value_array_keys`: Front Matter中以Key-Value—Arrays形式翻译

### 目标语言配置详情

由于使用的是谷歌翻译接口，所以目标语言需要使用ISO 639-1语言代码，具体可以参考[List of ISO 639-1 codes - Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)，下面给出一些常用的语言代码

| 语言名称   | 该语言自称                     | 语言代码 |
| ---------- | ------------------------------ | -------- |
| Chinese    | 漢語、汉语、华语               | zh       |
| English    | English                        | en       |
| Japanese   | 日本語                         | ja       |
| Spanish    | Español                        | es       |
| Russian    | русский                        | ru       |
| French     | français                       | fr       |
| German     | Deutsch                        | de       |
| Arabic     | العربية                        | ar       |
| Hindi      | हिन्दी                          | hi       |
| Portuguese | Português                      | pt       |
| Korean     | 한국어／韓國語, 朝鮮말／조선말 | ko       |

