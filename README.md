![Free-Markdown-Translator](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+Translators+%E7%9A%84%E5%85%8D%E8%B4%B9%E3%80%81%E5%BC%80%E6%BA%90%E7%9A%84Markdown%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8%EF%BC%8C%E8%83%BD%E5%A4%9F%E5%B0%86%E4%BD%A0%E7%9A%84Markdown%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E6%88%90%E4%BB%BB%E6%84%8F%E7%A7%8D%E8%AF%AD%E8%A8%80%E3%80%82&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

[English](doc/README.en.md) | [繁體中文](doc/README.zh-tw.md) | [Deutsch](doc/README.de.md) | [日本語](doc/README.ja.md) | [русский](doc/README.ru.md) | [한국어](doc/README.ko.md) | [Português](doc/README.pt.md) | [Español](doc/README.es.md) | [Français](doc/README.fr.md) | [हिन्दी](doc/README.hi.md)

## 简介

Free Markdown Translator是一款基于 [Translators](https://github.com/UlionTse/translators) 的**免费**、**开源**的Markdown文档翻译器，能够将你的Markdown文档翻译成**多种**语言。

功能：

- 将Markdown文档翻译成任意种语言
- 支持包含Google, Bing, alibaba, sogou, youdao, tencent, baidu等多种翻译引擎
- 支持使用**大语言模型（LLM）**进行高质量翻译（如 OpenAI、DeepSeek、通义千问、智谱等，需自行提供 API Key）
- 基本不会破坏Markdown文档原有的格式
- 支持并发翻译
- 支持添加多个文件夹、一个文件夹下的多个文件，对于特定场景十分便捷
- 支持在机器翻译的Markdown文档中添加警告语

本程序参考[如何使用translate.google.cn免費Google翻譯網站翻譯整篇Markdown文檔, V2修改版 (knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## 安装与运行

注意，若使用谷歌翻译等未在中国大陆提供服务的翻译引擎，在中国大陆等地区可能需要配置代理方能正常使用。

可执行程序使用同一目录下的`config.yaml`文件作为配置文件，当`config.yaml`缺失时，使用默认配置，配置详情参考`配置`小节的内容。

1. 下载右侧的发行版（MarkdownTranslator(vx.y).zip）
2. 解压后双击启动程序，然后键入Markdown文档的路径或文件夹的路径进行翻译
3. 或者在控制台中使用以下命令进行翻译

```bash
usage: MarkdownTranslator.py [-h] [-f FILE_OR_FOLDER [FILE_OR_FOLDER ...]]
                             [--continue | --rewrite]

Free Markdown Translator - translate Markdown documents into multiple languages.

默认行为：当目标输出文件已存在时跳过该翻译任务。
可以通过 --continue / --rewrite 控制已存在输出文件的处理方式。

options:
  -h, --help            show this help message and exit
  -f FILE_OR_FOLDER [FILE_OR_FOLDER ...]
                        要翻译的 Markdown 文档或文件夹路径；可同时指定多个。
  --continue            若目标输出文件已存在，则为该文件生成带数字后缀的新文件（例如
                        a.md -> a.1.md）。
  --rewrite             若目标输出文件已存在，则直接覆盖该文件的内容。
```

参数位置放置待翻译的文件或文件夹，可以添加多个文件夹，程序会自动按顺序翻译每个文件夹下的每个在配置文件中指定的文件。

例如，若指定的目标语言为英语(en)、日本语(ja)，则`readme.md`文件会被翻译到同文件夹下的`readme.en.md`,`readme.ja.md`。

使用 LLM 翻译时，输出文件名会带上引擎和模型信息，例如：

- 传统引擎：`README.en.google.md`
- LLM 引擎：`README.zh.llm.gpt-4o-mini.md`

便于同时保留多种翻译版本进行对比。

### 使用 LLM（大模型）翻译

从 vX.X 起支持通过大语言模型进行翻译，上下文与术语表现更好，输出文件名会带 `.llm.<模型名>`（如 `README.zh.llm.gpt-4o-mini.md`）。

**三步启用：**

1. **安装依赖**
   ```bash
   pip install openai httpx python-dotenv
   ```

2. **配置 `.env`**（项目根目录，勿提交到 Git）
   ```bash
   LLM_MODEL_URL=https://api.openai.com/v1
   LLM_MODEL_NAME=gpt-4o-mini
   LLM_MODEL_API_KEY=sk-xxxxxxxxxxxxxxxx
   # 可选：代理
   https_proxy=http://127.0.0.1:7890
   http_proxy=http://127.0.0.1:7890
   ```

3. **切换引擎并运行**
   - 在 `src/config.yaml` 中设置 `translator: llm`，其余配置（`target_langs`、`src_filenames`、`threads` 等）与传统引擎相同。
   - 运行：`cd src && python MarkdownTranslator.py -f ../README.md`

**环境变量：**

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_MODEL_URL` | API 基础地址 | `https://api.openai.com/v1` |
| `LLM_MODEL_NAME` | 模型名 | `gpt-4o-mini`、`deepseek-chat`、`qwen-plus`、`glm-4` |
| `LLM_MODEL_API_KEY` | API 密钥 | `sk-xxxx...` |

**支持的服务**：所有 OpenAI 兼容 API，如 OpenAI、DeepSeek、通义千问（`dashscope.aliyuncs.com/compatible-mode/v1`）、智谱（`open.bigmodel.cn/api/paas/v4/`）等。国内使用 OpenAI 时可在 `.env` 中配置 `https_proxy`/`http_proxy`。

**常见问题：**
- 提示缺少 API Key → 确认项目根目录有 `.env` 且含 `LLM_MODEL_API_KEY`。
- 导入失败 → 执行 `pip install openai httpx python-dotenv`。
- 切换回传统引擎 → 在 `config.yaml` 中把 `translator: llm` 改为 `translator: google` 等。

## 配置

请在与可执行程序使用同一目录下的`config.yaml`中进行配置，有关`yaml`文本格式的说明可以参考：[What is YAML? ](https://www.redhat.com/en/topics/automation/what-is-yaml)

1. `insert_warnings`: 控制是否在文档前面添加由机器翻译的警告
2. `src_language`: 指定源语言，auto表示由谷歌自动识别
3. `target_langs`: 需要翻译的目标语言
4. `translator`: 使用的翻译引擎，支持 google, bing, alibaba, sogou, youdao, tencent, baidu；设为 `llm` 时使用大语言模型翻译（需配置 `.env` 或下方 `llm_config`）
5. `llm_config`:（可选）LLM 翻译器配置，仅当 `translator: llm` 时生效；不配置则从项目根目录 `.env` 读取
6. `src_filenames`: 文件目录下需要自动检测并翻译的Markdown文档的名称
7. `threads`: 翻译时使用的最大线程数
8. `chunk_size_chars`: 每个 chunk 的目标字符数（影响分段长度）
9. `llm_context_before_lines` / `llm_context_after_lines`: 仅当 `translator: llm` 时生效，为每个 chunk 提供的上下文行数
10. `proxy`: 配置代理
11. `warnings_mapping`: 对应语言的由机器翻译警告的具体内容
12. `compact_langs`: 紧凑型语言，解决英语等非紧凑型语言的分隔问题
13. `front_matter_transparent_keys`: markdown的Front Matter中不用翻译的部分
14. `front_matter_key_value_keys`: Front Matter中需要以Key-Value形式翻译的部分
15. `front_matter_key_value_array_keys`: Front Matter中以Key-Value-Arrays形式翻译

示例配置文件：

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

# 使用的翻译引擎，支持 google, bing, alibaba, sogou, youdao, tencent, baidu；
# 设置为 'llm' 使用大语言模型进行翻译（需配置 .env 或下方 llm_config）
translator: google
# ---------- 可选：LLM 翻译器配置（仅当 translator: llm 时生效）----------
# 不配置则从项目根目录 .env 读取 LLM_MODEL_URL / LLM_MODEL_NAME / LLM_MODEL_API_KEY
# llm_config:
#   api_base: 'https://api.openai.com/v1'
#   model: gpt-4o-mini
#   api_key: 'sk-xxx'
#   temperature: 0.3
#   max_tokens: 2000

# 文件目录下需要翻译的文档的名称
src_filenames:
  - 'index'
  - 'README'
  - '_index'

# 翻译时使用的最大线程数，不超过30，小于等于0表示使用默认线程数
threads: -1

# --- chunking / LLM 上下文窗口（仅 translator=llm 时后两项生效）---
chunk_size_chars: 500
llm_context_before_lines: 0
llm_context_after_lines: 0

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

### 目标语言配置详情

目标语言需要使用ISO 639-1语言代码，具体可以参考[List of ISO 639-1 codes - Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)，下面给出一些常用的语言代码

| 语言名称   | 该语言自称                     | 语言代码 |
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

## Star History

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
