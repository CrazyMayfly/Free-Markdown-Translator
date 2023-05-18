# Free Markdown Translator

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![made-with-javascript](https://img.shields.io/badge/Made%20with-JavaScript-1f425f.svg)](https://www.javascript.com)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

> 警告：本文由機器翻譯生成，可能導致質量不佳或信息有誤，請謹慎閱讀！

## 簡介

Free Markdown Translator是一款基於Google Translate API 的免費、開源的Markdown文檔（以下簡稱md）翻譯器，能夠將你的md翻譯成任意種語言。

功能：

- 將md翻譯成任意種語言
- 不會破壞md原有的格式，同時支持自定義翻譯規則
- 支持多線程翻譯，同時加入了負載均衡機制，能夠有效地利用谷歌翻譯接口並且避免文檔翻譯失敗的發生
- 支持一次程序運行翻譯多個文件夾、一個文件夾下的多個文件，增加了便捷性
- 支持在機器翻譯的md中添加警告語

Google Translate API參考[VictorZhang2014/free-google-translate: Free Google Translator API 免費的Google翻譯 (github.com)](https://github.com/VictorZhang2014/free-google-translate)，本程序參考[如何使用translate.google.cn免費Google翻譯網站翻譯整篇Markdown文檔, V2修改版 (knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## 安裝與運行

1. 將倉庫克隆或將源代碼下載到本地

```bash
git clone git@github.com:AprilInJuly/Free-Markdown-Translator.git
```

2. 安裝軟件包`PyExecJS`

```bash
pip install PyExecJS
```

3. 進入代碼目錄，運行代碼

```bash
python.exe .\MarkdownTranslator.py
```

### 用法

```bash
python.exe MarkdownTranslator.py [-h] folder [folder ...]
```

參數位置放置待翻譯的文件夾，可以添加多個文件夾，程序會自動按順序翻譯每個文件夾下的每個在配置文件中指定的文件。

例如，若指定的目標語言為英語(en)、日本語(ja)，則`readme.md`文件會被翻譯到同文件夾下的`readme.en.md`,`readme.ja.md`。

## 配置

請在`config.py`中進行配置

1. `insert_warnings`: 控制是否在文章前面添加機器翻譯的Warning
2. `src_language`: 指定源語言，auto表示由谷歌自動識別
3. `warnings_mapping`: 配置目標語言的warning
4. `dest_langs`: 配置目標語言，可以手動指定目標語言，也可以直接使用`warnings_mapping`中配置的目標語言，按照定義順序翻譯
5. `skipped_regexs`: 指定要跳過翻譯的字符的正則表達式
6. `detect_filenames`: 文件目錄下需要翻譯的md文檔的名稱
7. `front_matter_transparent_keys`: markdown的Front Matter中不用翻譯的部分
8. `front_matter_key_value_keys`: Front Matter中需要以Key-Value形式翻譯的部分
9. `front_matter_key_value_array_keys`: Front Matter中以Key-Value—Arrays形式翻譯

### 目標語言配置詳情

由於使用的是谷歌翻譯接口，所以目標語言需要使用ISO 639-1語言代碼，具體可以參考[List of ISO 639-1 codes - Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)，下面給出一些常用的語言代碼

| 語言名稱       | 該語言自稱            | 語言代碼 |
|------------|------------------|------|
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


