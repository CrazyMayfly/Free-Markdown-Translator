# Traducteur Markdown gratuit

> Attention : cet article est traduit par machine, ce qui peut entraîner une mauvaise qualité ou des informations incorrectes, veuillez lire attentivement !


[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://github.com/CrazyMayfly/Free-Markdown-Translator/issues)

## Brève introduction

Le traducteur gratuit de la marque est basé sur [Traducteurs](https://github.com/UlionTse/translators) Le traducteur de document Markdown gratuit et open source peut traduire votre document Markdown en tout type de langue.

Fonction:

- Traduire le document Markdown en tout type de langue
- Le support contient une variété de moteurs de traduction tels que Google, Bing, Alibaba, Sogou, Youdao, Tencent, Baidu et d'autres moteurs de traduction
- Fondamentalement, il ne détruira pas le format d'origine du document Markdown
- Prise en charge de la traduction simultanée
- Prise en charge de plusieurs dossiers et plusieurs fichiers dans un dossier, ce qui est très pratique pour des scènes spécifiques
- Prise en charge d'ajouter des avertissements au document Markdown de la traduction machine

Référence pour ce programme [Comment utiliser tradlate.google.cn Site Web de traduction Google gratuit pour traduire l'intégralité du document Markdown, V2 Modified Version (Knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## Installation et fonctionnement

Notez que si vous utilisez Google Translation et d'autres moteurs de traduction qui n'ont pas fourni de services en Chine continentale, vous devrez peut-être connecter des agents en Chine continentale et d'autres régions pour les utiliser normalement.

Le programme exécutable utilise le même répertoire sous le même répertoire `config.yaml` Le fichier est utilisé comme fichier de configuration, devrait `config.yaml` En cas de manque, utilisez la configuration par défaut, les détails de la configuration, reportez-vous au contenu de la section.

1. Téléchargez la version de version à droite
2. Après décompression, double-cliquez sur le programme de démarrage, puis tapez le chemin du document Markdown ou le chemin du dossier de traduction
3. Ou utilisez des commandes dans la console pour traduire

```bash
usage: MarkdownTranslator.exe [-h] [-f file/folder [file/folder ...]]

Markdown translator, which translates markdown documents to target languages
you want.

options:
  -h, --help            show this help message and exit
  -f file/folder [file/folder ...]
                        the markdown documents or folders to translate.
```

Placez les fichiers ou les dossiers à traduire en position de paramètre, vous pouvez ajouter plusieurs dossiers et le programme traduira automatiquement chacun des fichiers spécifiés dans le fichier de configuration dans chaque dossier dans l'ordre.

Par exemple, si la langue cible spécifiée est l'anglais (en), le japonais (JA), alors `readme.md` Le fichier sera traduit dans le même dossier `readme.en.md`,`readme.ja.md` Essence

## Configuration

Veuillez utiliser le même répertoire que le programme exécutable `config.yaml` Configuration, connexe `yaml` Les instructions du format de texte peuvent être référées:[Qu'est-ce que Yaml?](https://www.redhat.com/en/topics/automation/what-is-yaml)

1. `insert_warnings`: Contrôlez s'il faut ajouter des avertissements traduits par la machine devant le document

2. `src_language`: Spécifiez la langue source, Auto indique que Google s'identifie automatiquement

3. `warnings_mapping`: Le contenu spécifique du langage correspondant est traduit par l'avertissement de traduction automatique

4. `target_langs`: La langue cible qui doit être traduite

5. `src_filenames`: Le nom du document Markdown qui doit être détecté et traduit automatiquement dans le répertoire de fichiers

6. `compact_langs`: Langue compacte, résoudre la séparation de la langue non compacte comme l'anglais

7. `front_matter_transparent_keys`: Le devant de Markdown n'a pas besoin de traduire des pièces

8. `front_matter_key_value_keys`: Partie de la partie de la partie de la traduction sous forme de valeur clé

9. `front_matter_key_value_array_keys`: Traduction de la matière de front sous forme de réseaux clés

Exemple de fichier de configuration:

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

### Détails de configuration du langage cible

La langue cible doit utiliser le code linguistique ISO 639-1.[Liste des codes ISO 639-1 -Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes), Voici un code linguistique couramment utilisé

|Nom de langue|Cette langue prétend|Code linguistique|
| ---------- | ------------------------------ | -------- |
|Chinois|Chinois, chinois, chinois|zh|
|ANGLAIS|ANGLAIS|En|
|japonais|japonais|ja|
|Espagnol|Español|Es|
|russe|sombre|ru|
|Français|Fransais|Frousser|
|Allemand|Deutsch|de|
|arabe|Sombre|Arde|
|hindi|Sombre|Salut|
|portugais|Portugugs|Pt|
|coréen|/ Corée, Corée du Nord 말 / 조선말|Ko|