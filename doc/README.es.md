# Traductor de markdown gratis

> Advertencia: este artículo está traducido por una máquina, lo que puede dar lugar a una mala calidad o información incorrecta. ¡Lea atentamente!


[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

## Breve introducción

El traductor de Markdown gratuito está basado en [Traductores](https://github.com/UlionTse/translators) El traductor de documentos de marca gratuito y de código abierto puede traducir su documento de Markdown en cualquier tipo de idioma.

Función:

- Traducir el documento de Markdown en cualquier tipo de idioma
- El soporte contiene una variedad de motores de traducción como Google, Bing, Alibaba, Sogou, Yodao, Tencent, Baidu y otros motores de traducción
- Básicamente, no destruirá el formato original del documento de Markdown
- Apoyo a la traducción concurrente
- Admite múltiples carpetas y múltiples archivos en una carpeta, que es muy conveniente para escenas específicas
- Soporte para agregar advertencias al documento de Markdown de traducción automática

Referencia para este programa [Cómo usar traduce.google.cn Sitio web gratuito de traducción de Google para traducir todo el documento de Markdown, versión modificada V2 (knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## Instalación y operación

Tenga en cuenta que si utiliza la traducción de Google y otros motores de traducción que no han brindado servicios en China continental, es posible que deba conectar a los agentes en China continental y otras regiones para usarlos normalmente.

El programa ejecutable utiliza el mismo directorio en el mismo directorio `config.yaml` El archivo se usa como un archivo de configuración, debe `config.yaml` Al faltar, use la configuración predeterminada, los detalles de configuración, consulte el contenido de la sección.

1. Descargue la versión de lanzamiento a la derecha
2. Después de la descompresión, haga doble clic en el programa de inicio y luego escriba la ruta del documento de Markdown o la ruta de la carpeta para la traducción
3. O usar comandos en la consola para traducir

```bash
usage: MarkdownTranslator.exe [-h] [-f file/folder [file/folder ...]]

Markdown translator, which translates markdown documents to target languages
you want.

options:
  -h, --help            show this help message and exit
  -f file/folder [file/folder ...]
                        the markdown documents or folders to translate.
```

Coloque los archivos o carpetas para traducir a la posición del parámetro, puede agregar varias carpetas y el programa traducirá automáticamente cada uno de los archivos especificados en el archivo de configuración en cada carpeta en orden.

Por ejemplo, si el idioma de destino especificado es inglés (EN), japonés (JA), entonces `readme.md` El archivo se traducirá a la misma carpeta `readme.en.md`,`readme.ja.md` Esencia

## Configuración

Utilice el mismo directorio que el programa ejecutable `config.yaml` Configuración, relacionado `yaml` Las instrucciones del formato de texto se pueden referir:[¿Qué es Yaml?](https://www.redhat.com/en/topics/automation/what-is-yaml)

1. `insert_warnings`: Controlar si agregar advertencias traducidas por la máquina frente al documento

2. `src_language`: Especifique el idioma de origen, automáticamente indica que Google identifica automáticamente

3. `warnings_mapping`: El contenido específico del idioma correspondiente se traduce mediante la advertencia de traducción automática

4. `target_langs`: El idioma de destino que debe traducirse

5. `src_filenames`: El nombre del documento Markdown que debe detectarse y traducirse automáticamente en el directorio de archivos

6. `compact_langs`: Lenguaje compacto, resolver la separación del idioma no compacto como el inglés

7. `front_matter_transparent_keys`: La materia frontal de Markdown no necesita traducir piezas

8. `front_matter_key_value_keys`: Materia frontal parte de la parte de la traducción en forma de valor clave

9. `front_matter_key_value_array_keys`: Traducción de la materia frontal en forma de rrayes de valores clave

Ejemplo de archivo de configuración:

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

### Detalles de configuración del idioma de destino

El idioma de destino debe usar el código de idioma ISO 639-1.[Lista de códigos ISO 639-1 -Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes), Aquí hay algún código de idioma de uso común

|Nombre del idioma|Este idioma afirma|Código de idioma|
| ---------- | ------------------------------ | -------- |
|Chino|Chino, chino, chino|zh|
|INGLÉS|INGLÉS|Interno|
|japonés|japonés|ja|
|Español|Español|Cepalle|
|ruso|desolado|freno|
|Francés|Fransais|Fría|
|Alemán|Deutsch|Delaware|
|árabe|Desolado|Arkansas|
|hindi|Desolado|Hola|
|portugués|Portugugs|PT|
|coreano|/Coreano, Corea del Norte 말/조선말|KO|