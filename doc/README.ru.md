#  Свободный переводчик

> Предупреждение: Эта статья переведена автоматически, что может привести к некачественной или неверной информации, пожалуйста, внимательно прочитайте!

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

##  Краткое введение

 Свободный переводчик разметки основан на [ Переводчики](https://github.com/UlionTse/translators)  Бесплатный и открытый документ с открытым исходным кодом может перевести ваш документ Markdown на любой тип языка.

 Функция:

-  Перевести документ Markdown на любой тип языка
-  Поддержка содержит различные переводчики, такие как Google, Bing, Deepl, Alibaba, Sogou, Youdao, Tencent, Baidu
-  По сути, это не разрушит первоначальный формат документа Markdown
-  Поддержка параллельного перевода
-  Поддержите несколько папок и несколько файлов в папке, что очень удобно для конкретных сцен
-  Поддержка для добавления предупреждений в документ Markdown машинного перевода

 Ссылка на эту программу [ Как использовать веб -сайт translate.google.cn бесплатный веб -сайт Google Translation для перевода всего документа Markdown, V2 Modified Version (Knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/) 

##  Установка и эксплуатация

 Обратите внимание, что если вы используете Google Translation и другие трансляционные двигатели, которые не предоставляли услуги в материковом Китае, вам может потребоваться подключить агентов в материковом Китае и других регионах, чтобы обычно его использовать.

 Исполняемая программа использует тот же каталог в рамках того же каталога `config.yaml`  Файл используется в качестве файла конфигурации, должен `config.yaml`  При отсутствии, используйте конфигурацию по умолчанию, сведения о конфигурации, см. Содержание раздела.

1.  Загрузите версию релиза справа
2.  После декомпрессии дважды -щелкните программу запуска, а затем введите путь документа Markdown или пути папки для перевода
3.  Или используйте команды в консоли для перевода

```bash
usage: MarkdownTranslator.exe [-h] [-f file/folder [file/folder ...]]

Markdown translator, which translates markdown documents to target languages
you want.

options:
  -h, --help            show this help message and exit
  -f file/folder [file/folder ...]
                        the markdown documents or folders to translate.
```

 Поместите файлы или папки, которые будут переведены в положение параметра, вы можете добавить несколько папок.

 Например, если указанный целевой язык - английский (en), японский (JA), то `readme.md`  Файл будет переведен в ту же папку `readme.en.md`  ,, `readme.ja.md`  Тогда тогда

##  Конфигурация

 Пожалуйста, используйте тот же каталог, что и исполняемая программа `config.yaml`  Конфигурация, связанная `yaml`  Для описания текстового формата, пожалуйста, см. [ Что такое ямл?](https://www.redhat.com/en/topics/automation/what-is-yaml) 

1.  `insert_warnings`  : Контролировать, добавлять ли предупреждения, переведенные машиной перед документом

2.  `src_language`  : Укажите исходный язык, Auto указывает, что Google автоматически идентифицирует

3.  `warnings_mapping`  : Конкретное содержание соответствующего языка переводится предупреждением о переводе машинного перевода

4.  `target_langs`  : Целевой язык, который необходимо перевести

5.  `src_filenames`  : Имя документа Markdown, которое необходимо обнаружить и перевести автоматически в каталоге файлов

6.  `compact_langs`  : Compact Language, Решение разделения некомпактного языка, такого как английский

7.  `front_matter_transparent_keys`  : Передняя материя Markdown не нужно переводить детали

8.  `front_matter_key_value_keys`  : Фронт должен быть ключом- Часть трансляции формы значения

9.  `front_matter_key_value_array_keys`  : Front Matter- Ценить- Массивы формируют перевод

 Пример файла конфигурации:

```yaml
# 控制是否在文章前面添加机器翻译的Warning
# 源语言,auto表示自动识别
insert_warnings: true
src_language: auto

# 使用的翻译引擎,支持google, deepl, bing, alibaba, sogou, youdao, tencent, baidu等翻译引擎
translator: google

# 配置目标语言及其warning,默认按照定义顺序翻译为下面语言
warnings_mapping:
  zh:  "警告：本文由机器翻译生成,可能导致质量不佳或信息有误,请谨慎阅读！" 
  zh-TW:  "警告：本文由機器翻譯生成,可能導致質量不佳或信息有誤,請謹慎閱讀！" 
  en:  "Warning: This page is translated by MACHINE, which may lead to POOR QUALITY or INCORRECT INFORMATION, please read with CAUTION!" 
  ja:  "警告: この記事は機械翻訳されているため、品質が低かったり不正確な情報が含まれる可能性があります. よくお読みください. " 
  ru:  "Предупреждение: Эта статья переведена автоматически, что может привести к некачественной или неверной информации, пожалуйста, внимательно прочитайте!" 
  es:  "Advertencia: este artículo está traducido por una máquina, lo que puede dar lugar a una mala calidad o información incorrecta. ¡Lea atentamente!" 
  fr:  "Attention : cet article est traduit par machine, ce qui peut entraîner une mauvaise qualité ou des informations incorrectes, veuillez lire attentivement !" 
  de:  "Achtung: Dieser Artikel wurde maschinell übersetzt, was zu schlechter Qualität oder falschen Informationen führen kann, bitte sorgfältig lesen!" 
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

###  Детали конфигурации целевого языка

 Целевой язык должен использоваться с помощью ISO 639- 1 языковой код, вы можете обратиться к нему для получения подробной информации [ Список ISO 639- 1 коды- Википедия](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)  , Вот несколько широко используемых языкового кода

| Имя языка| Этот язык утверждает| Языковой код|
|----------|------------------------------|--------|
| китайский| Китайский, китайский, китайский| ZH|
| АНГЛИЙСКИЙ| АНГЛИЙСКИЙ| Поступка|
| Японский| Японский| JA|
| испанский| Эспаньол| Эс|
| Русский| мрачный| Ру|
| Французский| Fransais| Фр|
| немецкий| Deutsch| де|
| арабский| Мрачный| АР|
| хинди| Мрачный| Привет|
| португальский| Португугс| Пт|
| корейский| , / Корея, Северная Корея 말 / 조선말| Носитель|


