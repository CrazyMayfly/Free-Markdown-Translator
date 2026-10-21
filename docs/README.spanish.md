![Traductor-Markdown-Gratuito](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

# Traductor Markdown Gratuito

Traductor Markdown Gratuito es una herramienta de traducción de documentos Markdown basada en un pipeline de agentes de IA que puede traducir documentos Markdown a cualquier idioma. Se centra en preservar la estructura original de Markdown tanto como sea posible durante el proceso de traducción, manteniendo al mismo tiempo la coherencia semántica. Es adecuado para escenarios como sitios de documentación, bases de conocimiento locales, README, documentos técnicos multilingües, etc. ✨

## 🚀 Principales funciones y características

- 🧠 Utiliza un proceso de traducción impulsado por IA y validación de árbol de sintaxis AST para mantener la estabilidad del formato y una coherencia contextual más consistente
- ✂️ Permite personalizar el estilo del idioma, la coincidencia de entrada y el formato de salida. Admite diferentes modos de traducción (rápido, equilibrado, estricto) para adaptarse a diferentes necesidades
- 🤖 Incorpora `TranslatorAgent`, `ReviewerAgent`, `FormatGuardAgent`, responsables respectivamente de la traducción, revisión y reparación de formato (habilitado según el modo de traducción)
- 🧱 Soporta protección de estructuras como front matter, niveles de encabezado, listas, tablas, bloques de código, enlaces, etc.
- ✅ Proporciona validación de estructura e informes de salida para ayudar a detectar deriva de formato y anomalías de contenido
- 🔌 Compatible con la interfaz estilo OpenAI, se puede conectar a OpenAI u otros servicios compatibles
- ⚙️ Soporta múltiples idiomas objetivo, traducción recursiva de directorios, procesamiento paralelo, restricciones de estilo de escritura y conservación de terminología

## ⚡ Inicio Rápido

### Método 1: Iniciar después de clonar el repositorio

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config
```

Después de la inicialización, el archivo de configuración predeterminado se generará en:

```text
~/.mdtx/config.yaml
```

Después de configurar la API Key, puedes comenzar a traducir:

```bash
python src/cli/main.py README.md --to english,japanese
```

### Método 2: Descargar el exe y usar directamente

Si estás usando Windows, también puedes descargar el `mdtx.exe` ya empaquetado y ejecutarlo directamente. Para el primer uso, se recomienda inicializar la configuración primero:

```powershell
.\mdtx.exe --init-config
```

Luego edita:

```text
~/.mdtx/config.yaml
```

Después de completar la configuración, puedes ejecutar:

```powershell
.\mdtx.exe README.md --to Chinese
```

### Ejemplos de comandos para escenarios comunes

Traducir un solo archivo al chino:

```bash
.\mdtx.exe README.md --to Chinese
```

Traducir recursivamente todo el directorio `doc` al inglés y japonés:

```bash
.\mdtx.exe doc --to english,japanese
```

Especificar directorio de salida:

```bash
.\mdtx.exe README.md --to Chinese --output translated
```

Coincidir solo con archivos Markdown con el formato de nombre de archivo especificado en el directorio (usando expresiones regulares):

```bash
.\mdtx.exe docs --to Chinese --match "name*.md"
```

Aumentar el paralelismo, acelerar la traducción por lotes grandes:

```bash
.\mdtx.exe docs --to Chinese --threads 10
```

Habilitar un proceso de traducción y validación más estricto, consume más tokens, toma más tiempo pero obtiene mejores resultados de traducción:

```bash
.\mdtx.exe docs --to Chinese --mode quality
```

Forzar la habilitación de revisión y protección de formato:

```bash
.\mdtx.exe docs --to Chinese --review true --guard true
```

Cambiar modelo o estilo de escritura:

```bash
.\mdtx.exe README.md --to Chinese --model gpt-5-mini --tone technical
```

Generar registros detallados, facilitar la solución de problemas:

```bash
.\mdtx.exe --verbose README.md --to Chinese
```

## ⚙️ Configuración

El proyecto buscará el archivo de configuración en el siguiente orden de prioridad:

1. `--config` ruta especificada
2.  en el directorio raíz del repositorio
3. `src/config.yaml`
4. `~/.mdtx/config.yaml`

Una configuración típica es la siguiente:

```yaml
# 目标语言列表。支持一次翻译为多个语言。
target_languages:
  - english
  - japanese

# 执行设置。
execution:
  # 全局 bundle 级最大并行翻译数。
  max_parallel_translations: 10
  
# 大模型服务配置。当前实现为 OpenAI 兼容接口。
provider:
  name: openai
  base_url: https://api.openai.com/v1
  # 推荐通过环境变量提供密钥；如需直填，可写在 api_key。
  api_key:
  api_key_env: OPENAI_API_KEY
  model: gpt-4o
  # 温度越低，输出越稳定。
  temperature: 0.2
  # 单次响应的最大 token 数。
  max_tokens: 8000

# 翻译流程控制。
pipeline:
  # fast: 省 token/提速（不跑 LLM 审校/终审）；balanced: 默认（只审可疑包）；quality: 最高质量（全量审校 + 终审，strict 为兼容别名）。
  mode: balanced
  # 强制开启审校 Agent。关闭时，balanced 只审可疑包，quality 全量审校。
  enable_review: false
  # 强制开启格式修复 Agent。关闭时，balanced/quality 遇到校验失败仍可能触发修复。
  enable_format_guard: false
  # 输出校验失败时是否直接报错。
  fail_on_validation_error: true

# 分段策略。先按 Markdown 结构（标题/列表/表格/引用）打包，超长块再按行拆分。
segmentation:
  max_bundle_tokens: 4000
  min_bundle_tokens: 1000

# 输入规则。
input:
  # 当传入目录时，递归匹配需要翻译的文件。
  file_pattern: "*.md"

# 文风与术语约束，会注入翻译上下文。
style:
  tone: technical
  audience: developers
  # 不翻译的专有名词或术语列表，会注入上下文并在翻译过程中保护。
  preserve_terms:
    - OpenAI
    - Markdown
    - Python
  instructions:
    - Keep protected placeholders unchanged.
    - Do not alter Markdown control syntax.

# 输出设置。
output:
  # 所有翻译结果会输出到这个目录下，并尽量保留原目录层级。
  directory: output
  # 可用变量：{stem} 原文件名，{lang} 目标语言缩写。
  file_suffix_template: "{stem}.{lang}.md"
  # 是否同时写出 *.report.json 报告。
  write_report: false
```

### Ejemplo de configuración de API Key

Se recomienda utilizar variables de entorno:

```powershell
$env:OPENAI_API_KEY="your-api-key"
.\mdtx.exe README.md --to Chinese
```

También puede escribirse en el archivo de configuración (no recomendado, presenta riesgos de seguridad):

```yaml
provider:
  api_key: xxxxx
```

Si utilizas una interfaz compatible, también puedes modificarlo en `config.yaml`:

```yaml
provider:
  name: openai
  base_url: https://your-openai-compatible-endpoint/v1
  api_key_env: YOUR_API_KEY_ENV
  model: your-model-name
```

## 🔄 Flujo de ejecución y mecanismo

Este proyecto no consiste en "enviar todo el Markdown al modelo para traducir de una vez", sino en un pipeline más seguro:

1. `MarkdownParser` Primero analiza el documento fuente en un AST, identificando la estructura Markdown
2. `SegmentExtractor` Extrae fragmentos traducibles del AST y protege contenido sensible como placeholders, sintaxis de control, etc.
3. `DocumentContextBuilder` Genera un resumen del documento, restricciones de estilo y contexto de terminología
4. `Orchestrator` Organiza los segmentos en múltiples bundles según la configuración, controlando el tamaño de cada llamada al modelo
5. `TranslatorAgent` Traduce cada bundle
6. `ReviewerAgent` realiza una revisión condicional en modo `balanced` / `quality`
7. `MarkdownRenderer` vuelve a mapear los resultados de la traducción al AST y los renderiza como Markdown
8. `MarkdownValidator` valida el front matter y la estructura general
9. Si la validación falla, `FormatGuardAgent` intentará reparar los problemas de formato cuando sea necesario
10. Finalmente genera el Markdown traducido y archivos de informe opcionales

El objetivo de este mecanismo es: preservar al máximo la apariencia original del Markdown, mientras se garantiza que los resultados de la traducción posean suficiente consistencia contextual y mantenibilidad. 🛡️

## 🗂️ Estructura del proyecto

```text
src/
├─ agents/        Agent 定义与提示词，负责翻译、审校、格式保护
├─ cli/           命令行入口与参数处理
├─ core/          流水线、任务编排、核心数据结构
├─ infra/         配置加载与日志基础设施
├─ llm/           模型客户端、Provider 封装、Schema
├─ memory/        文档上下文和翻译记忆相关组件
├─ parser/        Markdown 解析、AST 映射、渲染、分段
├─ validators/    front matter 与结构校验
└─ buildtool/     Windows exe 打包脚本与资源
```

Otros archivos importantes en el directorio raíz:

- `config.yaml`: Configuración de ejemplo
- `requirements.txt`: Dependencias de ejecución
- `doc/`: README multilingüe y documentos de diseño

## 🧪 Desarrollo y pruebas

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Si planeas empaquetar el exe tú mismo, también necesitarás:

```bash
pip install -r src/buildtool/requirements-build.txt
```

## Historial de Stars

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
