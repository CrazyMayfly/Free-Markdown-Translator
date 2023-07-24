# 無料のマークダウン翻訳者

> 警告: この記事は機械翻訳されているため、品質が低かったり不正確な情報が含まれる可能性があります。よくお読みください。

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![made-with-javascript](https://img.shields.io/badge/Made%20with-JavaScript-1f425f.svg)](https://www.javascript.com)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

## 簡単な紹介

Free Markdown Translatorは、Google Translate APIに基づいた無料のオープンソースMarkdownドキュメント（以下MDと呼ばれる）翻訳者であり、MDをあらゆるタイプの言語に翻訳できます。

関数：

- MDをあらゆるタイプの言語に変換します
- カスタム翻訳ルールをサポートしながら、MDの元の形式を破壊することはありません
- マルチスレッド翻訳をサポートし、同時に負荷分散メカニズムを追加します。これにより、Google翻訳インターフェイスを効果的に使用し、ドキュメント翻訳の障害を回避できます。
- 1つのフォルダーの下で複数のフォルダーと複数のファイルを実行するプログラムをサポートすると、利便性が向上します
- 機械翻訳のMDに警告を追加するためのサポート

Google翻訳APIリファレンス[victorzhang2014/free-グーグル-翻訳：無料のGoogle翻訳者API無料Google翻訳（github.com）](https://github.com/VictorZhang2014/free-google-translate)このプログラムリファレンス[Translate.google.cn無料のGoogle翻訳Webサイトの使用方法Markdownドキュメント全体を翻訳するために、V2 Modifiedバージョン（Knightli.com）](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## インストールと操作

このプログラムはGoogleの翻訳に依存しており、中国本土や他の地域のエージェントに接続する必要があることに注意してください。

### 実行可能なプログラムのインストールと使用

実行可能ファイル手順はデフォルトの構成によって使用されます。構成を変更することはできません。デフォルトで10を超えるターゲット言語への翻訳は、私の時間とエネルギーが制限されているため、構成が構成ファイルに書き込まれないことです。パーソナライズされた構成が必要な場合は、ソースコードをクローニングしてください。

1. 右側のリリースバージョンをダウンロードします
2. システムコンソールを開き、コンソールのエージェントを設定します
3. コンソールに次のコマンドを入力します

```bash
MarkdownTranslator.exe [-h] folder [folder ...]
```

フォルダーをパラメーター位置用に翻訳するように配置すると、複数のフォルダーを追加できます。プログラムは、構成ファイルで指定されたファイル内の各フォルダーを順番に自動的に変換します。

たとえば、指定されたターゲット言語が英語（EN）、日本語（JA）の場合、`readme.md`ファイルは同じフォルダーに翻訳されます`readme.en.md`、、、、`readme.ja.md`次に、

### ソースコードのクローニングと使用

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
python.exe MarkdownTranslator.py [-h] folder [folder ...]
```

フォルダーをパラメーター位置用に翻訳するように配置すると、複数のフォルダーを追加できます。プログラムは、構成ファイルで指定されたファイル内の各フォルダーを順番に自動的に変換します。

たとえば、指定されたターゲット言語が英語（EN）、日本語（JA）の場合、`readme.md`ファイルは同じフォルダーに翻訳されます`readme.en.md`、、、、`readme.ja.md`次に、

## 構成

でお願いします`config.py`構成

1. `insert_warnings`：記事の前に機械翻訳を追加するかどうかを制御する
2. `src_language`：ソース言語を指定し、AutoはGoogleが自動的に識別することを示します
3. `warnings_mapping`：ターゲット言語のタロンを構成します
4. `dest_langs`：ターゲット言語の構成、ターゲット言語を手動で指定するか、直接使用できます`warnings_mapping`構成内のターゲット言語は、定義の順に翻訳されます
5. `skipped_regexs`：翻訳をスキップするためにキャラクターの正規表現を指定します
6. `detect_filenames`：ファイルディレクトリに翻訳する必要があるMDドキュメントの名前
7. `front_matter_transparent_keys`：マークダウンのフロントマターは部品を翻訳する必要はありません
8. `front_matter_key_value_keys`：フロントマターはキーである必要があります-値フォーム翻訳部品
9. `front_matter_key_value_array_keys`： フロントの問題-値-rrays形式の翻訳

### ターゲット言語構成の詳細

Google翻訳インターフェイスが使用されるため、ターゲット言語はISO 639で使用する必要があります-1言語コード、詳細については参照できます[ISO 639のリスト-1つのコード- ウィキペディア](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)、ここにいくつかの一般的に使用される言語コードがあります

| 言語名| この言語は主張しています| 言語コード|
| ---------- | ------------------------------ | -------- |
| 中国語| 中国語、中国語、中国語| Zh|
| 英語| 英語| en|
| 日本| 日本| JA|
| スペイン語| スペイン語| es|
| ロシア| 暗い| ru|
| フランス語| フランサイス| fr|
| ドイツ人| ドイツ| de|
| アラビア語| 暗い| ar|
| ヒンディー語| 暗い| やあ|
| ポルトガル語| ポルトガグ| pt|
| 韓国語| 、 /韓国、北朝鮮말 /조선말| KO|


