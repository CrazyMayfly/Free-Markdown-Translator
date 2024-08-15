# 무료 Markdown 번역기

> 경고: 이 기사는 기계 번역으로 생성되어 품질이 좋지 않거나 잘못된 정보로 이어질 수 있으므로 주의 깊게 읽으십시오!


 [![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/) 
 [![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://github.com/CrazyMayfly/Free-Markdown-Translator/issues) 

## 간단한 소개

무료 Markdown Translator는 기반입니다 [번역가](https://github.com/UlionTse/translators)~의 **무료**,**오픈 소스** markdown 문서 번역기, Markdown 문서를 다음으로 변환 할 수 있습니다.**다수의** 언어.

기능:

- Markdown 문서를 모든 유형의 언어로 변환하십시오
- 지원에는 Google, Bing, Alibaba, Sogou, Youdao, Tencent, Baidu 및 기타 번역 엔진과 같은 다양한 번역 엔진이 포함되어 있습니다.
- 기본적으로 Markdown 문서의 원래 형식을 파괴하지 않습니다.
- 동시 번역을 지원하십시오
- 특정 장면에 매우 편리한 폴더 아래의 여러 폴더와 여러 파일을 지원합니다.
- 기계 번역의 Markdown 문서에 경고 추가 지원

이 프로그램에 대한 참조 [Translate.google.cn 무료 Google Translation 웹 사이트를 사용하는 방법 전체 Markdown 문서, V2 Modified Version (Knightli.com)을 번역하십시오.](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/) 

## 설치 및 작동

중국 본토에서 서비스를 제공하지 않은 Google 번역 및 기타 번역 엔진을 사용하는 경우 중국 본토 및 기타 지역의 에이전트를 정상적으로 사용하도록 구성해야 할 수도 있습니다.

실행 프로그램은 동일한 디렉토리에서 동일한 디렉토리를 사용합니다.`config.yaml` 파일은 구성 파일로 사용됩니다.`config.yaml` 누락 된 경우 기본 구성을 사용하고 구성 세부 사항을 참조하십시오.`구성` 섹션의 내용.

1. 오른쪽에 릴리스 버전을 다운로드하십시오
2. 감압 후 시작 프로그램을 두 번 클릭 한 다음 Markdown 문서의 경로 또는 번역 폴더 경로를 입력하십시오.
3. 또는 콘솔에서 다음 명령을 사용하여 번역하십시오.

```bash
usage: MarkdownTranslator.exe [-h] [-f file/folder [file/folder ...]]

Markdown translator, which translates markdown documents to target languages
you want.

options:
  -h, --help            show this help message and exit
  -f file/folder [file/folder ...]
                        the markdown documents or folders to translate.
```

파일 또는 폴더를 매개 변수 위치로 변환 할 수 있도록 여러 폴더를 추가 할 수 있으며 프로그램은 각 폴더의 구성 파일에 지정된 파일을 순서대로 자동 번역합니다.

예를 들어, 지정된 대상 언어가 영어 (en), 일본어 (JA) 인 경우 `readme.md` 파일은 동일한 폴더로 변환됩니다 `readme.en.md`,`readme.ja.md`.

## 구성

실행 프로그램과 동일한 디렉토리를 사용하십시오 `config.yaml` 구성, 관련 `yaml` 텍스트 형식에 대한 설명은 다음을 참조하십시오.[Yaml은 무엇입니까?](https://www.redhat.com/en/topics/automation/what-is-yaml) 

1. `insert_warnings`: 문서 앞에서 기계에서 번역 한 경고를 추가할지 여부
2. `src_language`: 소스 언어 지정, 자동은 Google이 자동으로 식별한다는 의미입니다.
3. `target_langs`: 번역 해야하는 대상 언어
4. `translator`: 사용 된 번역 엔진은 Google, Bing, Alibaba, Sogou, Youdao, Tencent, Baidu 및 기타 번역 엔진을 지원합니다.
5. `src_filenames`: 파일 디렉토리에서 자동으로 감지 및 번역 해야하는 Markdown 문서의 이름
6. `threads`: 번역 중에 사용되는 최대 스레드 수
7. `proxy`: 프록시를 구성하십시오
8. `warnings_mapping`: 해당 언어의 특정 내용은 기계 번역 경고에 의해 번역됩니다.
9. `compact_langs`: 컴팩트 언어, 영어와 같은 비 동정 언어의 분리 해결
10.`front_matter_transparent_keys`: Markdown의 전면 물질은 부품을 번역 할 필요가 없습니다.
11.`front_matter_key_value_keys`: 키 값 형태의 번역 부분의 전면 물질 부분
12.`front_matter_key_value_array_keys`: 키-값-rray의 형태의 프론트 물질 번역

구성 파일 예 :

```yaml
# 控制是否在文章前面添加机器翻译的Warning
insert_warnings: true

# 源语言，auto表示自动识别
src_language: auto

# 目标语言
target_langs:
  - zh
  - en
  - ja
  - ru

# 使用的翻译引擎，支持google, bing, alibaba, sogou, youdao, tencent, baidu等翻译引擎
translator: google

# 文件目录下需要翻译的文档的名称
src_filenames:
  - 'index'
  - 'README'
  - '_index'

# 翻译时使用的最大线程数，不超过30，小于等于0表示使用默认线程数
threads: -1

# 配置代理
proxy:
    # 是否启用代理
    enable: false
    # 代理地址
    address: 127.0.0.1
    # 代理端口
    port: 1234
    # 代理用户名和密码
    username:
    password:

# 配置目标语言及其warning，默认按照定义顺序翻译为下面语言
warnings_mapping:
  zh: "警告：本文由机器翻译生成，可能导致质量不佳或信息有误，请谨慎阅读！" 
  zh-TW: "警告：本文由機器翻譯生成，可能導致質量不佳或信息有誤，請謹慎閱讀！" 
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

# 紧凑型语言，解决英语等非紧凑型语言的分隔问题
compact_langs:
  - zh-TW
  - ja

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

### 대상 언어 구성 세부 사항

대상 언어는 ISO 639-1 언어 코드를 사용해야합니다 [ISO 639-1 코드 목록 -Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) 다음은 일반적으로 사용되는 언어 코드가 있습니다

|언어 이름|이 언어는 주장합니다|언어 코드|
| ---------- | ------------------------------ | -------- |
|중국인|중국어, 중국어, 중국어|ZH|
|영어|영어|~에 의해|
|일본어|日本語|이미|
|스페인 사람|스페인 사람|~이다|
|러시아인|ртттт 기술|ru|
|프랑스 국민|프랑스 국민|정말로|
|형제|도이치치|~의|
|아라비아 말|الررر승자|가다|
|힌디 어|더 많이보십시오|거기|
|포르투갈 인|포르투갈 인|Pt|
|Korean|한국어／韓國語, 朝鮮말／조선말|ko|
