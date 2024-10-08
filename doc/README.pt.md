# Translator de marcação livre

> Aviso: Este artigo é traduzido por máquina, o que pode levar a má qualidade ou informações incorretas, leia com atenção!


 [![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/) 
 [![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://github.com/CrazyMayfly/Free-Markdown-Translator/issues) 

## Breve introdução

O tradutor de marcação livre é um baseado em [Tradutores](https://github.com/UlionTse/translators) de **livre**,**Código aberto** document tradutor de documentos de marcação, que pode traduzir seu documento de marcação em **Múltiplo** linguagem.

Função:

- Traduzir o documento de remarque em qualquer tipo de linguagem
- O suporte contém uma variedade de motores de tradução, como Google, Bing, Alibaba, Sogou, Youdao, Tencent, Baidu e outros motores de tradução
- Basicamente, ele não destruirá o formato original do documento de marcação
- Suporte tradução simultânea
- Suporte a várias pastas e vários arquivos em uma pasta, o que é muito conveniente para cenas específicas
- Suporte para adicionar avisos ao documento de marcação da tradução da máquina

Referência para este programa [Como usar o site de tradução do Google GRATUITO para usar o Documento de Markdown inteiro, versão modificada da V2 (Knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/) 

## Instalação e operação

Observe que, se você usar o Google Translation e outros mecanismos de tradução que não prestaram serviços na China continental, pode ser necessário configurar agentes na China continental e em outras regiões para usá -los normalmente.

O programa executável usa o mesmo diretório no mesmo diretório `config.yaml` O arquivo é usado como um arquivo de configuração, deve `config.yaml` quando estiver ausente, use a configuração padrão, detalhes de configuração consulte `Configuração` O conteúdo da seção.

1. Baixe a versão de lançamento à direita
2. Após a descompressão, clique duas vezes no programa de inicialização e digite o caminho do documento de marcação ou o caminho da pasta para tradução
3. Ou use os seguintes comandos no console para traduzir

```bash
usage: MarkdownTranslator.exe [-h] [-f file/folder [file/folder ...]]

Markdown translator, which translates markdown documents to target languages
you want.

options:
  -h, --help            show this help message and exit
  -f file/folder [file/folder ...]
                        the markdown documents or folders to translate.
```

Coloque os arquivos ou pastas a serem traduzidos para a posição do parâmetro, você pode adicionar várias pastas e o programa traduzirá automaticamente o arquivo especificado no arquivo de configuração em cada pasta em ordem.

Por exemplo, se o idioma de destino especificado for inglês (en), japonês (JA), então `readme.md` O arquivo será traduzido para a mesma pasta `readme.en.md`,`readme.ja.md`.

## Configuração

Use o mesmo diretório que o programa executável `config.yaml` configuração, relacionada `yaml` para descrição do formato de texto, consulte: Consulte:[O que é Yaml?](https://www.redhat.com/en/topics/automation/what-is-yaml) 

1. `insert_warnings`: Controle se deve adicionar avisos traduzidos pela máquina em frente ao documento
2. `src_language`: Especificar o idioma de origem, automaticamente significa que o Google identifica automaticamente
3. `target_langs`: O idioma de destino que precisa ser traduzido
4. `translator`: O mecanismo de tradução utilizado, suporta Google, Bing, Alibaba, Sogou, Youdao, Tencent, Baidu e outros motores de tradução
5. `src_filenames`: O nome do documento de remarkdown que precisa ser detectado e traduzido automaticamente no diretório de arquivos
6. `threads`: O número máximo de threads usados ​​durante a tradução
7. `proxy`: Configurar proxy
8. `warnings_mapping`: O conteúdo específico do idioma correspondente é traduzido pelo aviso de tradução da máquina
9. `compact_langs`: Linguagem compacta, resolvendo a separação de linguagem não compacta, como o inglês
10.`front_matter_transparent_keys`: O assunto da frente de Markdown não precisa traduzir peças
11.`front_matter_key_value_keys`: Parte da matéria da frente da parte da tradução na forma de valor-chave
12.`front_matter_key_value_array_keys`: Tradução de matéria frontal na forma de rrânulos-chave-valor

Exemplo de arquivo de configuração:

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

### Detalhes de configuração de idioma de destino

O idioma de destino precisa usar o código ISO 639-1.[Lista de códigos ISO 639-1 -Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes), Aqui estão algum código de idioma comumente usado

|Nome do idioma|Este idioma afirma|Código do idioma|
| ---------- | ------------------------------ | -------- |
|chinês|Chinês, chinês, chinês|Zh|
|Inglês|Inglês|por|
|japonês|日本語|já|
|espanhol|Espanhol|é|
|russo|``|ru|
|Francês|Francês|fr|
|Irmão|Deutsch|de|
|árabe|الربية|ir|
|hindi|Veja mais de|lá|
|Português|Português|pt|
|coreano|Língua coreana / coreana, Joseon|Ko|
