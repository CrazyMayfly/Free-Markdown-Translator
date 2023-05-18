# 無料のマークダウン翻訳者

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![made-with-javascript](https://img.shields.io/badge/Made%20with-JavaScript-1f425f.svg)](https://www.javascript.com)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

> 警告: この記事は機械翻訳されているため、品質が低かったり不正確な情報が含まれる可能性があります。よくお読みください。

## 簡単な紹介

Free Markdown Translatorは、Google Translate APIに基づいた無料のオープンソースMarkdownドキュメント（以下MDと呼ばれる）翻訳者であり、MDをあらゆるタイプの言語に翻訳できます。

関数：

- MDをあらゆるタイプの言語に変換します
- カスタム翻訳ルールをサポートしながら、MDの元の形式を破壊することはありません
- マルチスレッド翻訳をサポートし、同時に負荷分散メカニズムを追加します。これにより、Google翻訳インターフェイスを効果的に使用し、ドキュメント翻訳の障害を回避できます。
- 1つのフォルダーの下で複数のフォルダーと複数のファイルを実行するプログラムをサポートすると、利便性が向上します
- 機械翻訳のMDに警告を追加するためのサポート

Google翻訳APIリファレンス[victorzhang2014/free-グーグル-翻訳：無料のGoogle翻訳者API無料Google翻訳（github.com）](https://github.com/VictorZhang2014/free-google-translate)、このプログラムリファレンス[Translate.google.cn無料のGoogle翻訳Webサイトの使用方法Markdownドキュメント全体を翻訳するために、V2 Modifiedバージョン（Knightli.com）](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## インストールと操作

1. 倉庫をダウンロードするか、ソースコードをローカルエリアにダウンロードしてください

```bash
git clone git@github.com:AprilInJuly/Free-Markdown-Translator.git
```

2. ソフトウェアパッケージをインストールします`PyExecJS`

```bash
pip install PyExecJS
```

3. コードディレクトリを入力し、コードを実行します

```bash
python.exe .\MarkdownTranslator.py
```

### 使用法

```bash
python.exe MarkdownTranslator.py [-h] folder [folder ...]
```

パラメーター位置用に翻訳するフォルダーを配置すると、複数のフォルダーを追加できます。プログラムは、ファイル内の各フォルダーを構成ファイルに自動的に変換します。

たとえば、指定されたターゲット言語が英語（EN）、日本語（JA）の場合、`readme.md`ファイルは同じフォルダーに翻訳されます`readme.en.md`、`readme.ja.md`次に、

## 構成

でお願いします`config.py`構成

1. `insert_warnings`：記事の前に機械翻訳を追加するかどうかを制御する
2. `src_language`：ソース言語を指定し、自動はGoogleが自動的に識別することを意味します
3. `warnings_mapping`：ターゲット言語のタロンを構成します
4. `dest_langs`：ターゲット言語の構成、ターゲット言語を手動で指定するか、直接使用できます`warnings_mapping`中央で構成されたターゲット言語は、定義の順に翻訳されます
5. `skipped_regexs`：翻訳をスキップするためにキャラクターの正規表現を指定します
6. `detect_filenames`：ファイルディレクトリに翻訳する必要があるMDドキュメントの名前
7. `front_matter_transparent_keys`：マークダウンのフロントマターは部品を翻訳する必要はありません
8. `front_matter_key_value_keys`：フロントマターはキーである必要があります-値フォーム翻訳部品
9. `front_matter_key_value_array_keys`： フロントの問題-値-rrays形式の翻訳

### ターゲット言語構成の詳細

Google翻訳インターフェイスが使用されているため、ターゲット言語はISO 639を使用する必要があります-1言語コード、詳細については参照できます[ISO 639のリスト-1つのコード- ウィキペディア](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)、ここにいくつかの一般的に使用される言語コードがあります

| 言語名| この言語は主張しています| 言語コード|
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


