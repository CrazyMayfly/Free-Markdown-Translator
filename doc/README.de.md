# Kostenloser Markdown -Übersetzer

> Achtung: Dieser Artikel wurde maschinell übersetzt, was zu schlechter Qualität oder falschen Informationen führen kann, bitte sorgfältig lesen!


[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://github.com/CrazyMayfly/Free-Markdown-Translator/issues)

## Kurze Einführung

Der kostenlose Markdown -Übersetzer basiert auf [Übersetzer](https://github.com/UlionTse/translators) Der KOSTENLOSE- und Open -Source -Dokumentenübersetzer kann Ihr Markdown -Dokument in eine beliebige Art von Sprache übersetzen.

Funktion:

- Übersetzen Sie das Markdown -Dokument in jede Art von Sprache
- Die Unterstützung enthält eine Vielzahl von Übersetzungsmotoren wie Google, Bing, Alibaba, Sogou, YouDao, Tencent, Baidu und andere Übersetzungsmotoren
- Grundsätzlich wird es nicht das ursprüngliche Format des Markdown -Dokuments zerstören
- Unterstützung bei gleichzeitiger Übersetzung
- Unterstützen Sie mehrere Ordner und mehrere Dateien unter einem Ordner, was für bestimmte Szenen sehr bequem ist
- Unterstützung, um dem Markdown -Dokument der maschinellen Übersetzung Warnungen hinzuzufügen

Referenz für dieses Programm [So verwenden Sie translate.google.cn kostenlose Google -Übersetzungs -Website, um das gesamte Markdown -Dokument, V2 Modified Version (Knightli.com), zu übersetzen.](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## Installation und Betrieb

Beachten Sie, dass Sie, wenn Sie Google Translation und andere Übersetzungsmotoren verwenden, die keine Dienste auf dem chinesischen Festland erbracht haben, möglicherweise Agenten auf dem chinesischen Festland und anderen Regionen verbinden, um sie normal zu verwenden.

Das ausführbare Programm verwendet das gleiche Verzeichnis im selben Verzeichnis `config.yaml` Die Datei wird als Konfigurationsdatei verwendet, sollte `config.yaml` Verwenden Sie beim Fehlen der Standardkonfiguration, Konfigurationsdetails und finden Sie in den Inhalt des Abschnitts.

1. Laden Sie die Release -Version rechts herunter
2. Nach der Dekompression verdoppeln Sie das Startprogramm und geben Sie dann den Pfad des Markdown -Dokuments oder den Pfad des Ordners zur Übersetzung ein
3. Oder verwenden Sie Befehle in der Konsole, um sie zu übersetzen

```bash
usage: MarkdownTranslator.exe [-h] [-f file/folder [file/folder ...]]

Markdown translator, which translates markdown documents to target languages
you want.

options:
  -h, --help            show this help message and exit
  -f file/folder [file/folder ...]
                        the markdown documents or folders to translate.
```

Platzieren Sie die Dateien oder Ordner, die in die Parameterposition übersetzt werden sollen, Sie können mehrere Ordner hinzufügen. Das Programm übersetzt automatisch jede der in der Konfigurationsdatei angegebenen Dateien in jedem Ordner in der Reihenfolge.

Zum Beispiel, wenn die angegebene Zielsprache Englisch (EN), Japanisch (JA) ist, dann `readme.md` Die Datei wird in denselben Ordner übersetzt `readme.en.md`,`readme.ja.md` Wesen

## Konfiguration

Bitte verwenden Sie das gleiche Verzeichnis wie das ausführbare Programm `config.yaml` Konfiguration, verwandt `yaml` Die Anweisungen des Textformats können bezeichnet werden:[Was ist Yaml?](https://www.redhat.com/en/topics/automation/what-is-yaml)

1. `insert_warnings`: Kontrolle, ob von der Maschine vor dem Dokument übersetztes Warnungen hinzugefügt werden soll

2. `src_language`: Geben Sie die Quellsprache an, auto zeigt an, dass Google automatisch identifiziert

3. `warnings_mapping`: Der spezifische Inhalt der entsprechenden Sprache wird durch die maschinelle Übersetzungswarnung übersetzt

4. `target_langs`: Die Zielsprache, die übersetzt werden muss

5. `src_filenames`: Der Name des Markdown -Dokuments, das im Dateiverzeichnis automatisch erkannt und übersetzt werden muss

6. `compact_langs`: Kompakte Sprache, Lösung der Trennung von nicht kompakten Sprache wie Englisch

7. `front_matter_transparent_keys`: Markdowns Front Materie muss keine Teile übersetzen

8. `front_matter_key_value_keys`: Front Materie Teil des Teils der Übersetzung in Form des Schlüsselwerts

9. `front_matter_key_value_array_keys`: Vordermaterie-Übersetzung in Form von Schlüsselwert-Rätseln

Beispielkonfigurationsdatei:

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

### Details zur Konfiguration der Zielsprachenkonfiguration

Die Zielsprache muss ISO 639-1 Sprachcode verwenden.[Liste der ISO 639-1 -Codes -wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) Hier sind einige häufig verwendete Sprachcode

|Sprachname|Diese Sprache behauptet an|Sprachcode|
| ---------- | ------------------------------ | -------- |
|chinesisch|Chinesisch, Chinesisch, Chinesisch|Zh|
|ENGLISCH|ENGLISCH|En|
|japanisch|japanisch|Ja|
|Spanisch|Español|Es|
|Russisch|kahl|Ru|
|Französisch|Fransais|Fr|
|Deutsch|Deutsch|de|
|Arabisch|Kahl|Ar|
|Hindi|Kahl|Hallo|
|Portugiesisch|Portugugs|Pt|
|Koreanisch|/Koreanisch, Nordkorea 말/조선말|Ko|