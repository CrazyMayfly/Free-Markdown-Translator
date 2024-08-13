# Free Markdown Translator

> Warning: This page is translated by MACHINE, which may lead to POOR QUALITY or INCORRECT INFORMATION, please read with CAUTION!


[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

## Brief introduction

Free Markdown Translator is a based on [Translators](https://github.com/UlionTse/translators) The free and open source Markdown document translator can translate your Markdown document into any type of language.

Function:

- Translate the MarkDown document into any type of language
- Support contains a variety of translation engines such as Google, Bing, Alibaba, Sogou, YOUDAO, Tencent, BAIDU and other translation engines
- Basically, it will not destroy the original format of the Markdown document
- Support concurrent translation
- Support multiple folders and multiple files under a folder, which is very convenient for specific scenes
- Support to add warnings to the Markdown document of machine translation

Reference for this program [How to use translate.google.cn free Google translation website to translate the entire Markdown document, v2 modified version (knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## Installation and operation

Note that if you use Google Translation and other translation engines that have not provided services in mainland China, you may need to connect agents in mainland China and other regions to use them normally.

The executable program uses the same directory under the same directory `config.yaml` The file is used as a configuration file, should `config.yaml` When lacking, use the default configuration, configuration details, refer to the content of the section.

1. Download the release version on the right
2. After decompression, double -click the startup program, and then type the path of the Markdown document or the path of the folder for translation
3. Or use commands in the console to translate

```bash
usage: MarkdownTranslator.exe [-h] [-f file/folder [file/folder ...]]

Markdown translator, which translates markdown documents to target languages
you want.

options:
  -h, --help            show this help message and exit
  -f file/folder [file/folder ...]
                        the markdown documents or folders to translate.
```

Place the files or folders to be translated to the parameter position, you can add multiple folders, and the program will automatically translate each of the files specified in the configuration file in each folder in order.

For example, if the specified target language is English (EN), Japanese (JA), then `readme.md` The file will be translated to the same folder `readme.en.md`,`readme.ja.md` Essence

## Configuration

Please use the same directory as the executable program `config.yaml` Configuration, related `yaml` The instructions of the text format can be referred to:[What is yaml?](https://www.redhat.com/en/topics/automation/what-is-yaml)

1. `insert_warnings`: Control whether to add warnings translated by the machine in front of the document

2. `src_language`: Specify the source language, Auto indicates that Google automatically identifies

3. `warnings_mapping`: The specific content of the corresponding language is translated by the machine translation warning

4. `target_langs`: The target language that needs to be translated

5. `src_filenames`: The name of the Markdown document that needs to be detected and translated automatically in the file directory

6. `compact_langs`: Compact language, solving the separation of non -compact language such as English

7. `front_matter_transparent_keys`: Markdown's Front Matter does not need to translate parts

8. `front_matter_key_value_keys`: FRONT MATTER part of the part of translation in the form of key-value

9. `front_matter_key_value_array_keys`: FRONT MATTER translation in the form of Key-Value-Rrays

Example configuration file:

```yaml
# 控制是否在文章前面添加机器翻译的Warning
# 源语言,auto表示自动识别
insert_warnings: true
src_language: auto

# 使用的翻译引擎,支持google, bing, alibaba, sogou, youdao, tencent, baidu等翻译引擎
translator: google

# 配置目标语言及其warning,默认按照定义顺序翻译为下面语言
warnings_mapping:
  zh: "警告:本文由机器翻译生成,可能导致质量不佳或信息有误,请谨慎阅读!"
  zh-TW: "警告:本文由機器翻譯生成,可能導致質量不佳或信息有誤,請謹慎閱讀!"
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

# 指定目标语言
target_langs:
  - zh
  - en
  - ja
  - ru

# 紧凑型语言,解决英语等非紧凑型语言的分隔问题
compact_langs:
  - zh-TW
  - ja

# 文件目录下需要翻译的文档的名称
src_filenames:
  - 'index'
  - 'README'
  - '_index'

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
|ENGLISH|ENGLISH|EN|
|Japanese|Japanese|ja|
|Spanish|Español|ES|
|Russian|bleak|ru|
|French|Fransais|Fr|
|German|Deutsch|de|
|Arabic|Bleak|AR|
|Hindi|Bleak|Hi|
|Portuguese|Portugugs|PT|
|Korean|/Korean, North Korea 말/조선말|KO|