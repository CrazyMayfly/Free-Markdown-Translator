# 무료 Markdown 번역기

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![made-with-javascript](https://img.shields.io/badge/Made%20with-JavaScript-1f425f.svg)](https://www.javascript.com)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

> 경고: 이 기사는 기계 번역으로 생성되어 품질이 좋지 않거나 잘못된 정보로 이어질 수 있으므로 주의 깊게 읽으십시오!

## 간단한 소개

Free Markdown Translator는 Google Translate API를 기반으로 무료 오픈 소스 마크 다운 문서 (MD) 번역기로 MD를 모든 유형의 언어로 변환 할 수 있습니다.

기능:

- MD를 모든 유형의 언어로 변환하십시오
- 사용자 정의 번역 규칙을 지원하면서 원래 MD 형식을 파괴하지 않습니다.
- 멀티 스레드 변환을 지원하고 동시에로드 밸런싱 메커니즘을 추가하여 Google 번역 인터페이스를 효과적으로 사용하고 문서 변환의 실패를 피할 수 있습니다.
- 한 폴더에서 여러 폴더와 여러 파일을 실행하는 프로그램을 지원하여 편의성이 향상됩니다.
- 기계 번역의 MD에 경고를 추가하도록 지원합니다

Google 번역 API 참조[Victorzhang2014/무료-Google-번역 : 무료 Google Translator API 무료 Google Translation (github.com)](https://github.com/VictorZhang2014/free-google-translate),이 프로그램 참조[Translate.google.cn 무료 Google Translation 웹 사이트를 사용하는 방법 전체 Markdown 문서, V2 Modified Version (Knightli.com)을 번역하십시오.](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## 설치 및 작동

1. 창고를 다운로드하거나 소스 코드를 로컬 영역으로 다운로드하십시오.

```bash
git clone git@github.com:AprilInJuly/Free-Markdown-Translator.git
```

2. 소프트웨어 패키지를 설치하십시오`PyExecJS`

```bash
pip install PyExecJS
```

3. 코드 디렉토리를 입력하고 코드를 실행하십시오

```bash
python.exe .\MarkdownTranslator.py
```

### 용법

```bash
python.exe MarkdownTranslator.py [-h] folder [folder ...]
```

매개 변수 위치에 대해 변환 할 폴더를 배치하면 여러 폴더를 추가 할 수 있으며 프로그램은 구성 파일의 파일의 각 폴더를 자동으로 번역합니다.

예를 들어, 지정된 대상 언어가 영어 (en), 일본어 (JA) 인 경우`readme.md`파일은 동일한 폴더로 변환됩니다`readme.en.md`,,`readme.ja.md`그러면

## 구성

제발`config.py`구성

1. `insert_warnings`: 기사 앞에서 기계 번역 추가 여부 제어
2. `src_language`: 소스 언어 지정, 자동은 Google이 자동으로 식별한다는 의미입니다.
3. `warnings_mapping`: 대상 언어의 타로 닝을 구성하십시오
4. `dest_langs`: 대상 언어를 구성하거나 대상 언어를 수동으로 지정하거나 직접 사용할 수 있습니다.`warnings_mapping`중간에 구성된 대상 언어는 정의 순서로 변환됩니다.
5. `skipped_regexs`: 문자의 정규 표현을 지정하여 번역을 건너 뜁니다.
6. `detect_filenames`: 파일 디렉토리에서 번역 해야하는 MD ​​문서의 이름
7. `front_matter_transparent_keys`: Markdown의 전면 물질은 부품을 번역 할 필요가 없습니다.
8. `front_matter_key_value_keys`: 프론트 물질이 핵심이어야합니다-가치 형태 번역 부분
9. `front_matter_key_value_array_keys`: 서문-값 -Rrays 형식 변환

### 대상 언어 구성 세부 사항

Google 번역 인터페이스가 사용되므로 대상 언어는 ISO 639를 사용해야합니다.-1 언어 코드, 자세한 내용은 참조 할 수 있습니다.[ISO 639 목록-코드 1- 위키 백과](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)다음은 일반적으로 사용되는 언어 코드가 있습니다

| 언어 이름| 이 언어는 주장합니다| 언어 코드|
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

