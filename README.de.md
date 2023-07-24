# Kostenloser Markdown -Übersetzer

> Achtung: Dieser Artikel wurde maschinell übersetzt, was zu schlechter Qualität oder falschen Informationen führen kann, bitte sorgfältig lesen!

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![made-with-javascript](https://img.shields.io/badge/Made%20with-JavaScript-1f425f.svg)](https://www.javascript.com)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

## Kurze Einleitung

Der kostenlose Markdown -Übersetzer ist ein kostenloses Open -Source -Markdown -Dokument (im Folgenden als MD) -Translator basierend auf der API von Google Translate, mit der Ihr MD in eine beliebige Art von Sprache übersetzt werden kann.

Funktion:

- Übersetzen Sie MD in jede Art von Sprache
- Es wird das ursprüngliche Format von MD nicht zerstören, während die benutzerdefinierten Übersetzungsregeln unterstützt werden
- Unterstützen Sie multi -thread -Übersetzungen und fügen Sie gleichzeitig Lastausgleichsmechanismen hinzu, die effektiv Google Translation -Schnittstellen verwenden und den Fehler der Dokumentübersetzung vermeiden können.
- Unterstützen Sie ein Programm, um mehrere Ordner und mehrere Dateien unter einem Ordner auszuführen, was die Bequemlichkeit erhöht
- Unterstützung, um MDs der maschinellen Übersetzung Warnungen hinzuzufügen

Google Übersetzungs -API -Referenz [Victorzhang2014/kostenlos-Google-Übersetzung: Kostenlose Google Translator API kostenlose Google Translation (Github.com)](https://github.com/VictorZhang2014/free-google-translate) Diese Programmreferenz [So verwenden Sie translate.google.cn kostenlose Google -Übersetzungs -Website, um das gesamte Markdown -Dokument, V2 Modified Version (Knightli.com), zu übersetzen.](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/) 

## Installation und Betrieb

Beachten Sie, dass dieses Programm von Google Translation abhängt und mit Agenten auf dem chinesischen Festland und anderen Regionen verbunden sein muss, um sie zu verwenden.

### Performance Program Installation und Verwendung

Die ausführbare Prozedur wird von der Standardkonfiguration verwendet. Die Konfiguration kann nicht geändert werden. Die Übersetzung von Chinesen in mehr als 10 Zielsprachen standardmäßig ist, dass die Konfiguration nicht in die Konfigurationsdatei geschrieben ist. Wenn Sie eine personalisierte Konfiguration benötigen, klonieren Sie bitte den Quellcode.

1. Laden Sie die Release -Version rechts herunter
2. Öffnen Sie die Systemkonsole und setzen Sie einen Agenten für die Konsole
3. Geben Sie den folgenden Befehl in die Konsole ein

```bash
MarkdownTranslator.exe [-h] folder [folder ...]
```

Wenn Sie den Ordner für die Parameterposition übersetzt werden, können Sie mehrere Ordner hinzufügen. Das Programm übersetzt automatisch jeden Ordner in der in der Konfigurationsdatei angegebenen Datei in der Reihenfolge.

Zum Beispiel, wenn die angegebene Zielsprache Englisch (EN), Japanisch (JA) ist, dann `readme.md` Die Datei wird in denselben Ordner übersetzt `readme.en.md` ,,,, `readme.ja.md` Dann dann

### Quellcodeklonen und Verwendung

1. Laden Sie das Lagerhaus herunter oder laden Sie den Quellcode in die Region herunter

```bash
git clone git@github.com:AprilInJuly/Free-Markdown-Translator.git
```

2. Softwarepaket installieren `PyExecJS` 

```bash
pip install PyExecJS
```

3. Geben Sie das Code -Verzeichnis ein, führen Sie den Code aus

```bash
python.exe MarkdownTranslator.py [-h] folder [folder ...]
```

Wenn Sie den Ordner für die Parameterposition übersetzt werden, können Sie mehrere Ordner hinzufügen. Das Programm übersetzt automatisch jeden Ordner in der in der Konfigurationsdatei angegebenen Datei in der Reihenfolge.

Zum Beispiel, wenn die angegebene Zielsprache Englisch (EN), Japanisch (JA) ist, dann `readme.md` Die Datei wird in denselben Ordner übersetzt `readme.en.md` ,,,, `readme.ja.md` Dann dann

## Aufbau

Bitte um `config.py` Aufbau

1.  `insert_warnings` : Steuer, ob maschinelle Übersetzung vor dem Artikel hinzugefügt werden soll
2.  `src_language` : Geben Sie die Quellsprache an, auto zeigt an, dass Google automatisch identifiziert
3.  `warnings_mapping` : Konfigurieren Sie die Taronierung der Zielsprache
4.  `dest_langs` : Konfigurieren Sie die Zielsprache, Sie können die Zielsprache manuell angeben oder sie können sie direkt verwenden `warnings_mapping` Die Zielsprache in der Konfiguration wird in der Reihenfolge der Definition übersetzt
5.  `skipped_regexs` : Geben Sie den regulären Ausdruck des Zeichens an, um die Übersetzung zu überspringen
6.  `detect_filenames` : Der Name des MD -Dokuments, das im Dateiverzeichnis übersetzt werden muss
7.  `front_matter_transparent_keys` : Markdowns Front Materie muss keine Teile übersetzen
8.  `front_matter_key_value_keys` : Front Materie muss der Schlüssel sein-Wertformularübersetzungsteil
9.  `front_matter_key_value_array_keys` : Front Materie-Wert -Rrays Formatübersetzung

### Details zur Konfiguration der Zielsprachenkonfiguration

Da die Google -Übersetzungsschnittstelle verwendet wird, muss die Zielsprache von ISO 639 verwendet werden-1 Sprachcode, Sie können sich darauf verweisen, um Details zu erhalten [Liste der ISO 639-1 Codes- Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) Hier sind einige häufig verwendete Sprachcode

| Sprache Name| Diese Sprache behauptet an| Sprachcode|
| ---------- | ------------------------------ | -------- |
| Chinesisch| Chinesisch, Chinesisch, Chinesisch| Zh|
| ENGLISCH| ENGLISCH| En|
| japanisch| japanisch| Ja|
| Spanisch| Español| Es|
| Russisch| kahl| Ru|
| Französisch| Fransais| Fr|
| Deutsch| Deutsch| de|
| Arabisch| Kahl| Ar|
| Hindi| Kahl| Hallo|
| Portugiesisch| Portugugs| Pt|
| Koreanisch| , / Koreanisch, Nordkorea 말 / 조선말| Ko|


