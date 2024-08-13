# 無料のマークダウン翻訳者

> 警告: この記事は機械翻訳されているため、品質が低かったり不正確な情報が含まれる可能性があります。よくお読みください。


[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://github.com/CrazyMayfly/Free-Markdown-Translator/issues)

## 簡単な紹介

無料のマークダウン翻訳者はに基づいています[翻訳者](https://github.com/UlionTse/translators)無料およびオープンソースのマークダウンドキュメント翻訳者は、マークダウンドキュメントをあらゆるタイプの言語に翻訳できます。

関数：

- Markdownドキュメントをあらゆるタイプの言語に翻訳します
- サポートには、Google、Bing、Alibaba、Sogou、Youdao、Tencent、Baidu、その他の翻訳エンジンなどのさまざまな翻訳エンジンが含まれています
- 基本的に、マークダウンドキュメントの元の形式を破壊しません
- 同時翻訳をサポートします
- フォルダーの下で複数のフォルダーと複数のファイルをサポートします。これは、特定のシーンに非常に便利です
- 機械翻訳のマークダウンドキュメントに警告を追加するためのサポート

このプログラムのリファレンス[Translate.google.cn無料のGoogle翻訳Webサイトの使用方法Markdownドキュメント全体を翻訳するために、V2 Modifiedバージョン（Knightli.com）](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## インストールと操作

中国本土でサービスを提供していないGoogle翻訳やその他の翻訳エンジンを使用する場合は、中国本土や他の地域のエージェントを接続して正常に使用する必要がある場合があることに注意してください。

実行可能プログラムは、同じディレクトリの下に同じディレクトリを使用します`config.yaml`ファイルは構成ファイルとして使用されます、必要です`config.yaml`不足している場合は、デフォルトの構成、構成の詳細を使用して、セクションのコンテンツを参照してください。

1. 右側のリリースバージョンをダウンロードします
2. 減圧後、スタートアッププログラムをダブルクリックしてから、マークダウンドキュメントのパスまたは翻訳用のフォルダーのパスを入力します
3. または、コンソール内のコマンドを使用して翻訳します

```bash
usage: MarkdownTranslator.exe [-h] [-f file/folder [file/folder ...]]

Markdown translator, which translates markdown documents to target languages
you want.

options:
  -h, --help            show this help message and exit
  -f file/folder [file/folder ...]
                        the markdown documents or folders to translate.
```

ファイルまたはフォルダーをパラメーター位置に翻訳するように配置し、複数のフォルダーを追加できます。プログラムは、各フォルダーの構成ファイルに指定された各ファイルを順番に自動的に変換します。

たとえば、指定されたターゲット言語が英語（EN）、日本語（JA）の場合、`readme.md`ファイルは同じフォルダーに翻訳されます`readme.en.md`,`readme.ja.md`エッセンス

## 構成

実行可能ファイルプログラムと同じディレクトリを使用してください`config.yaml`構成、関連`yaml`テキスト形式の指示は次のように参照できます。[Yamlとは何ですか？](https://www.redhat.com/en/topics/automation/what-is-yaml)

1. `insert_warnings`：ドキュメントの前で機械によって翻訳された警告を追加するかどうかを制御する

2. `src_language`：ソース言語を指定し、AutoはGoogleが自動的に識別することを示します

3. `warnings_mapping`：対応する言語の特定の内容は、機械翻訳警告によって翻訳されます

4. `target_langs`：翻訳する必要があるターゲット言語

5. `src_filenames`：ファイルディレクトリで自動的に検出および翻訳する必要があるマークダウンドキュメントの名前

6. `compact_langs`：コンパクトな言語、英語などの非コンパクト言語の分離を解決する

7. `front_matter_transparent_keys`：マークダウンのフロントマターは部品を翻訳する必要はありません

8. `front_matter_key_value_keys`：キー価値の形で翻訳の部分の前部の部分

9. `front_matter_key_value_array_keys`：キー値のルレーの形式でのフロントマター翻訳

構成ファイルの例：

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

### ターゲット言語構成の詳細

ターゲット言語は、ISO 639-1言語コードを使用する必要があります[ISO 639-1コードのリスト-Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)、ここにいくつかの一般的に使用される言語コードがあります

|言語名|この言語は主張しています|言語コード|
| ---------- | ------------------------------ | -------- |
|中国語|中国語、中国語、中国語|Zh|
|英語|英語|en|
|日本語|日本語|JA|
|スペイン語|español|es|
|ロシア|暗い|ru|
|フランス語|フランサイス|fr|
|ドイツ語|ドイツ|de|
|アラビア語|暗い|ar|
|ヒンディー語|暗い|こんにちは|
|ポルトガル語|ポルトガグ|pt|
|韓国語|/韓国、北朝鮮말/조선말|KO|