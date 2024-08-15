# Free Markdown Translator

> Warning: This page is translated by MACHINE, which may lead to POOR QUALITY or INCORRECT INFORMATION, please read with CAUTION!

 [![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/) 
 [![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://github.com/CrazyMayfly/Free-Markdown-Translator/issues) 

## Brief introduction

Free Markdown Translator is a based on [Translators](https://github.com/UlionTse/translators) of **free**, **open source** markdown document translator, which can translate your Markdown document into **multiple** language.

Function:

- Translate the MarkDown document into any type of language
- Support contains a variety of translation engines such as Google, Bing, Alibaba, Sogou, YOUDAO, Tencent, BAIDU and other translation engines
- Basically, it will not destroy the original format of the Markdown document
- Support concurrent translation
- Support multiple folders and multiple files under a folder, which is very convenient for specific scenes
- Support to add warnings to the Markdown document of machine translation

Reference for this program [How to use translate.google.cn free Google translation website to translate the entire Markdown document, v2 modified version (knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/) 

## Installation and operation

Note that if you use Google Translation and other translation engines that have not provided services in mainland China, you may need to configure agents in mainland China and other regions to use them normally.

The executable program uses the same directory under the same directory `config.yaml` the file is used as a configuration file, should `config.yaml` when missing, use the default configuration, configuration details refer to `Configuration` the content of the section.

1. Download the release version on the right
2. After decompression, double -click the startup program, and then type the path of the Markdown document or the path of the folder for translation
3. Or use the following commands in the console to translate

```bash
usage: MarkdownTranslator.exe [-h] [-f file/folder [file/folder ...]]

Markdown translator, which translates markdown documents to target languages
you want.

options:
  -h, --help            show this help message and exit
  -f file/folder [file/folder ...]
                        the markdown documents or folders to translate.
```

Put the files or folders to be translated to the parameter position, you can add multiple folders, and the program will automatically translate the file specified in the configuration file in each folder in order.

For example, if the specified target language is English (EN), Japanese (JA), then `readme.md` the file will be translated to the same folder `readme.en.md`,`readme.ja.md`.

## Configuration

Please use the same directory as the executable program `config.yaml` configuration, related `yaml` for description of text format, please refer to:[What is yaml?](https://www.redhat.com/en/topics/automation/what-is-yaml) 

1. `insert_warnings`: Control whether to add warnings translated by the machine in front of the document
2. `src_language`: Specify the source language, Auto means that Google automatically identifies
3. `target_langs`: The target language that needs to be translated
4. `translator`: The translation engine used, supports Google, Bing, Alibaba, SOGOU, YOUDAO, TENCENT, BAIDU and other translation engines
5. `src_filenames`: The name of the Markdown document that needs to be detected and translated automatically in the file directory
6. `threads`: The maximum number of threads used during translation
7. `proxy`: Configure proxy
8. `warnings_mapping`: The specific content of the corresponding language is translated by the machine translation warning
9. `compact_langs`: Compact language, solving the separation of non -compact language such as English
10.`front_matter_transparent_keys`: Markdown's Front Matter does not need to translate parts
11.`front_matter_key_value_keys`: FRONT MATTER part of the part of translation in the form of key-value
12.`front_matter_key_value_array_keys`: FRONT MATTER translation in the form of Key-Value-Rrays

Example configuration file:

```yaml
# 控制是否在文章前面添加机器翻译的Warning
insert_warnings: true

# 源语言，auto表示自动识别
src_language: auto

# 目标语言
target_langs:
  - zh
  - en
  - ja
  - ru

# 使用的翻译引擎，支持google, bing, alibaba, sogou, youdao, tencent, baidu等翻译引擎
translator: google

# 文件目录下需要翻译的文档的名称
src_filenames:
  - 'index'
  - 'README'
  - '_index'

# 翻译时使用的最大线程数，不超过30，小于等于0表示使用默认线程数
threads: -1

# 配置代理
proxy:
    # 是否启用代理
    enable: false
    # 代理地址
    address: 127.0.0.1
    # 代理端口
    port: 1234
    # 代理用户名和密码
    username:
    password:

# 配置目标语言及其warning，默认按照定义顺序翻译为下面语言
warnings_mapping:
  zh: "警告：本文由机器翻译生成，可能导致质量不佳或信息有误，请谨慎阅读！" 
  zh-TW: "警告：本文由機器翻譯生成，可能導致質量不佳或信息有誤，請謹慎閱讀！" 
  en: "Warning: This page is translated by MACHINE, which may lead to POOR QUALITY or INCORRECT INFORMATION, please read with CAUTION!" 
  ja: "警告: この記事は機械翻訳されているため、品質が低かったり不正確な情報が含まれる可能性があります。よくお読みください。" 
  ru: "Предупреждение: Эта статья переведена автоматически, что может привести к некачественной или неверной информации, пожалуйста, внимательно прочитайте!" 
  es: "Advertencia: este artículo está traducido por una máquina, lo que puede dar lugar a una mala calidad o información incorrecta. ¡Lea atentamente!" 
  fr: "Attention : cet article est traduit par machine, ce qui peut entraîner une mauvaise qualité ou des informations incorrectes, veuillez lire attentivement !" 
  de: "Achtung: Dieser Artikel wurde maschinell übersetzt, was zu schlechter Qualität oder falschen Informationen führen kann, bitte sorgfältig lesen!" 
  # # 印地语
  hi: 'चेतावनी: यह लेख मशीन द्वारा अनुवादित है, जिससे खराब गुणवत्ता या गलत जानकारी हो सकती है, कृपया ध्यान से पढ़ें!'
  # 葡萄牙语
  pt: 'Aviso: Este artigo é traduzido por máquina, o que pode levar a má qualidade ou informações incorretas, leia com atenção!'
  # 韩语
  ko: '경고: 이 기사는 기계 번역으로 생성되어 품질이 좋지 않거나 잘못된 정보로 이어질 수 있으므로 주의 깊게 읽으십시오!'

# 紧凑型语言，解决英语等非紧凑型语言的分隔问题
compact_langs:
  - zh-TW
  - ja

# markdown中Front Matter不用翻译的部分
front_matter_transparent_keys:
  - 'date:'
  - 'slug:'
  - 'toc'
  - 'image'
  - 'comments'
  - 'readingTime'
  - 'menu:'
  - '    main:'
  - '        weight:'
  - '        params:'
  - '            icon:'
  - 'links:'
  - '    website:'
  - '    image:'
  - 'layout:'
  - 'outputs:'
  - '    - html'
  - '    - json'
  - 'license:'
  - '#'
  - 'style:'
  - '    background:'
  - '    color:'

# Front Matter中需要以Key-Value形式翻译的部分
front_matter_key_value_keys:
  - 'title:'
  - 'description:'
  - '        name:'
  - '  - title:'
  - '    description:'

# Front Matter中以Key-Value—Arrays形式翻译
front_matter_key_value_array_keys:
  - 'tags:'
  - 'categories:'
  - 'keywords:'
```

### Target language configuration details

The target language needs to use ISO 639-1 language code. For details, please refer to [List of ISO 639-1 Codes -Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes), Here are some commonly used language code

|Language name|This language claims to|Language code|
| ---------- | ------------------------------ | -------- |
|Chinese|Chinese, Chinese, Chinese|zh|
|English|English|by|
|Japanese|日本語|already|
|spanish|Spanish|is|
|Russian|ртттт|ru|
|French|French|fr|
|Brother|Deutsch|of|
|Arabic|الربية|go|
|Hindi|See more of|there|
|Portuguese|Portuguese|pt|
|Korean|Korean / Korean language, Joseon|ko|
