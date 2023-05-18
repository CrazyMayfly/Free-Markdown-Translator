# Free Markdown Translator

> Warning: This page is translated by MACHINE, which may lead to POOR QUALITY or INCORRECT INFORMATION, please read with CAUTION!

## Introduction

Free Markdown Translator is a free, open source Markdown document (hereinafter referred to as MD) translator based on Google Translate API, which can translate your MD into any type of language.

Function:

- Translate MD into any type of language
- It will not destroy the original format of MD, while supporting custom translation rules
- Support multi -threaded translation, and add load balancing mechanisms at the same time, which can effectively use Google translation interfaces and avoid the failure of document translation.
- Support a program to run multiple folders and multiple files under one folder, which increases convenience
- Support to add warnings to MDs of machine translation

Google Translate API Reference[Victorzhang2014/free-Google-Translate: Free Google Translator API free Google translation (github.com)](https://github.com/VictorZhang2014/free-google-translate), This program reference[How to use translate.google.cn free Google translation website to translate the entire Markdown document, v2 modified version (knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## Installation and operation

1. Download the warehouse or download the source code to the local area

```bash
git clone git@github.com:AprilInJuly/Free-Markdown-Translator.git
```

2. Install software package`PyExecJS`

```bash
pip install PyExecJS
```

3. Enter the code directory, run the code

```bash
python.exe .\MarkdownTranslator.py
```

### usage

```bash
python.exe MarkdownTranslator.py [-h] folder [folder ...]
```

Place the folder to be translated for the parameter position, you can add multiple folders, and the program will automatically translate each folder in the file in the configuration file.

For example, if the specified target language is English (EN), Japanese (JA), then`readme.md`The file will be translated to the same folder`readme.en.md`,`readme.ja.md`

## Configuration

please at`config.py`Configuration

1. `insert_warnings`: Control whether to add machine translation in front of the article
2. `src_language`: Specify the source language, Auto means that Google automatically identifies
3. `warnings_mapping`: Configure the taroning of the target language
4. `dest_langs`: Configure the target language, you can manually specify the target language, or you can use it directly`warnings_mapping`The target language configured in the middle is translated in the order of definition
5. `skipped_regexs`: Specify the regular expression of the character to skip the translation
6. `detect_filenames`: The name of the MD document that needs to be translated in the file directory
7. `front_matter_transparent_keys`: Markdown's Front Matter does not need to translate parts
8. `front_matter_key_value_keys`: FRONT MATTER needs to be key-Value form translation part
9. `front_matter_key_value_array_keys`: FRONT MATTER-Value -Rrays format translation

### Target language configuration details

Because the Google Translate API is used, the target language needs to use ISO 639-1 Language code, you can refer to it for details[List of ISO 639-1 codes- Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes), Here are some commonly used language code

| Language name| This language claims to| Language code|
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

