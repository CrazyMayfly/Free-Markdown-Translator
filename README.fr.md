# Traducteur Markdown gratuit

> Attention : cet article est traduit par machine, ce qui peut entraîner une mauvaise qualité ou des informations incorrectes, veuillez lire attentivement !

## Courte introduction

Le traducteur Markdown gratuit est un traducteur gratuit et open source (ci-après MD) basé sur l'API Google Translate, qui peut traduire votre MD dans n'importe quel type de langue.

Fonction:

- Traduire MD en tout type de langue
- Il ne détruira pas le format d'origine de MD, tout en prenant en charge les règles de traduction personnalisées
- Prise en charge de la traduction multi-thread et ajoutez des mécanismes d'équilibrage de charge en même temps, qui peuvent utiliser efficacement les interfaces de traduction Google et éviter la défaillance de la traduction du document.
- Prise en charge d'un programme pour exécuter plusieurs dossiers et plusieurs fichiers dans un seul dossier, ce qui augmente la commodité
- Support pour ajouter des avertissements aux MDS de la traduction automatique

Google Translate API référence[Victorzhang2014 / gratuit-Google-Traduire: API Google Traductrice gratuite Traduction Google gratuite (github.com)](https://github.com/VictorZhang2014/free-google-translate), Cette référence du programme[Comment utiliser tradlate.google.cn Site Web de traduction Google gratuit pour traduire l'intégralité du document Markdown, V2 Modified Version (Knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## Installation et fonctionnement

1. Téléchargez l'entrepôt ou téléchargez le code source dans la zone locale

```bash
git clone git@github.com:AprilInJuly/Free-Markdown-Translator.git
```

2. Installer un progiciel`PyExecJS`

```bash
pip install PyExecJS
```

3. Entrez le répertoire de code, exécutez le code

```bash
python.exe .\MarkdownTranslator.py
```

### usage

```bash
python.exe MarkdownTranslator.py [-h] folder [folder ...]
```

Placez le dossier à traduire pour la position du paramètre, vous pouvez ajouter plusieurs dossiers et le programme traduira automatiquement chaque dossier dans le fichier dans le fichier de configuration.

Par exemple, si la langue cible spécifiée est l'anglais (en), le japonais (JA), alors`readme.md`Le fichier sera traduit dans le même dossier`readme.en.md`,,`readme.ja.md`Alors, alors

## Configuration

s'il vous plaît à`config.py`Configuration

1. `insert_warnings`: Contrôlez s'il faut ajouter une traduction machine devant l'article
2. `src_language`: Spécifiez la langue source, Auto signifie que Google s'identifie automatiquement
3. `warnings_mapping`: Configurer le taroning de la langue cible
4. `dest_langs`: Configurer la langue cible, vous pouvez spécifier manuellement la langue cible, ou vous pouvez l'utiliser directement`warnings_mapping`Le langage cible configuré au milieu est traduit dans l'ordre de définition
5. `skipped_regexs`: Spécifiez l'expression régulière du personnage pour sauter la traduction
6. `detect_filenames`: Le nom du document MD qui doit être traduit dans le répertoire de fichiers
7. `front_matter_transparent_keys`: Le devant de Markdown n'a pas besoin de traduire des pièces
8. `front_matter_key_value_keys`: La matière avant doit être clé-Partie de la partie de la forme de formulaire
9. `front_matter_key_value_array_keys`: Front Matter-Valeur-Rays Format Traduction

### Détails de configuration du langage cible

Parce que l'interface de traduction Google est utilisée, le langage cible doit utiliser ISO 639-1 code linguistique, vous pouvez vous y référer pour plus de détails[Liste de l'ISO 639-1 codes- Wikipédia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes), Voici un code linguistique couramment utilisé

| Nom de la langue| Cette langue prétend| Code linguistique|
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

