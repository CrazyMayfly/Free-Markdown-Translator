# Translator de marcação livre

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![made-with-javascript](https://img.shields.io/badge/Made%20with-JavaScript-1f425f.svg)](https://www.javascript.com)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

> Aviso: Este artigo é traduzido por máquina, o que pode levar a má qualidade ou informações incorretas, leia com atenção!

## Breve introdução

O Livre Markdown Translator é um documento de marcação de código aberto gratuito (a seguir denominado tradutor de MD) com base na API do Google Translate, que pode traduzir seu MD em qualquer tipo de linguagem.

Função:

- Traduzir MD em qualquer tipo de linguagem
- Não destruirá o formato original do MD, enquanto apoia regras de tradução personalizadas
- Apoie a tradução multi -thread e adicione mecanismos de balanceamento de carga ao mesmo tempo, o que pode efetivamente usar interfaces de tradução do Google e evitar a falha da tradução do documento.
- Apoie um programa para executar várias pastas e vários arquivos em uma pasta, o que aumenta a conveniência
- Suporte para adicionar avisos ao MDS da tradução da máquina

Referência da API do Google Translate[Victorzhang2014/grátis-Google-Tradução: API do Google Tradutor gratuita gratuita do Google Tradução (github.com)](https://github.com/VictorZhang2014/free-google-translate), Esta referência do programa[Como usar o site de tradução do Google GRATUITO para usar o Documento de Markdown inteiro, versão modificada da V2 (Knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## Instalação e operação

1. Faça o download do armazém ou faça o download do código -fonte para a área local

```bash
git clone git@github.com:AprilInJuly/Free-Markdown-Translator.git
```

2. Instale o pacote de software`PyExecJS`

```bash
pip install PyExecJS
```

3. Digite o diretório de código, execute o código

```bash
python.exe .\MarkdownTranslator.py
```

### uso

```bash
python.exe MarkdownTranslator.py [-h] folder [folder ...]
```

Coloque a pasta a ser traduzida para a posição do parâmetro, você pode adicionar várias pastas e o programa traduzirá automaticamente cada pasta no arquivo no arquivo de configuração.

Por exemplo, se o idioma de destino especificado for inglês (en), japonês (JA), então`readme.md`O arquivo será traduzido para a mesma pasta`readme.en.md`,,`readme.ja.md`Então então

## Configuração

por favor em`config.py`Configuração

1. `insert_warnings`: Controle se deve adicionar a tradução da máquina na frente do artigo
2. `src_language`: Especificar o idioma de origem, automaticamente significa que o Google identifica automaticamente
3. `warnings_mapping`: Configure o taronamento da linguagem alvo
4. `dest_langs`: Configurar o idioma de destino, você pode especificar manualmente o idioma de destino ou pode usá -lo diretamente`warnings_mapping`A linguagem de destino configurada no meio é traduzida na ordem de definição
5. `skipped_regexs`: Especifique a expressão regular do personagem para pular a tradução
6. `detect_filenames`: O nome do documento do MD que precisa ser traduzido no diretório de arquivos
7. `front_matter_transparent_keys`: O assunto da frente de Markdown não precisa traduzir peças
8. `front_matter_key_value_keys`: O assunto da frente precisa ser fundamental-Parte de tradução do formulário de valor
9. `front_matter_key_value_array_keys`: Matéria frontal-Valor -Rrays Format Translation

### Detalhes de configuração de idioma de destino

Como a interface de tradução do Google é usada, a linguagem de destino precisa usar a ISO 639-1 Código de idioma, você pode consultar para os detalhes[Lista da ISO 639-1 códigos- Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes), Aqui estão algum código de idioma comumente usado

| Nome do idioma| Este idioma afirma| Código do idioma|
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
