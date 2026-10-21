![Free-Markdown-Translator](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

# Free Markdown Translator

Free Markdown Translator est un outil de traduction de documents Markdown basé sur un pipeline d'agents IA, capable de traduire des documents Markdown dans n'importe quelle langue. Il se concentre sur la préservation de la structure Markdown originale autant que possible pendant la traduction, tout en maintenant la cohérence sémantique. Il est adapté aux sites de documentation, bases de connaissances locales, README, documents techniques multilingues, etc. ✨

## 🚀 Principales fonctionnalités

- 🧠 Utilise un processus de traduction piloté par l'IA et une validation par arbre syntaxique AST pour maintenir la stabilité du format et une meilleure cohérence contextuelle
- ✂️ Permet de personnaliser le style linguistique, la correspondance des entrées et le format de sortie, prend en charge différents modes de traduction (rapide, équilibré, strict) pour s'adapter à différents besoins
- 🤖 Intègre `TranslatorAgent`, `ReviewerAgent`, `FormatGuardAgent`, respectivement responsables de la traduction, de la révision et de la correction du format (activés selon le mode de traduction)
- 🧱 Prend en charge la protection des structures telles que front matter, hiérarchie des titres, listes, tableaux, blocs de code, liens, etc.
- ✅ Fournit une validation de structure et un rapport de sortie, aidant à détecter la dérive de format et les anomalies de contenu
- 🔌 Compatible avec les interfaces de style OpenAI, peut se connecter à OpenAI ou à d'autres services compatibles
- ⚙️ Prend en charge plusieurs langues cibles, la traduction récursive de répertoires, le traitement parallèle, les contraintes de style et la conservation des termes

## ⚡ Démarrage rapide

### Méthode 1 : Cloner le dépôt puis démarrer

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config
```

Après l'initialisation, le fichier de configuration par défaut sera généré dans :

```text
~/.mdtx/config.yaml
```

Une fois la clé API configurée, vous pouvez commencer la traduction :

```bash
python src/cli/main.py README.md --to english,japanese
```

### Méthode 2 : Télécharger l'exécutable et l'utiliser directement

Si vous utilisez Windows, vous pouvez également télécharger le `mdtx.exe` déjà packagé et l'exécuter directement. Pour la première utilisation, il est recommandé d'initialiser la configuration d'abord :

```powershell
.\mdtx.exe --init-config
```

Ensuite, éditez :

```text
~/.mdtx/config.yaml
```

Une fois la configuration terminée, vous pouvez exécuter :

```powershell
.\mdtx.exe README.md --to Chinese
```

### Exemples de commandes pour des scénarios courants

Traduire un fichier unique en chinois :

```bash
.\mdtx.exe README.md --to Chinese
```

Traduire récursivement l'ensemble du répertoire `doc` en anglais et en japonais :

```bash
.\mdtx.exe doc --to english,japanese
```

Spécifier le répertoire de sortie :

```bash
.\mdtx.exe README.md --to Chinese --output translated
```

Ne cibler que les fichiers Markdown dont le nom correspond au format spécifié dans le répertoire (via regex) :

```bash
.\mdtx.exe docs --to Chinese --match "name*.md"
```

Augmenter le parallélisme pour accélérer les traductions en masse :

```bash
.\mdtx.exe docs --to Chinese --threads 10
```

Activer un processus de traduction et de validation plus strict, consommant plus de tokens et prenant plus de temps, mais offrant une meilleure qualité de traduction :

```bash
.\mdtx.exe docs --to Chinese --mode strict
```

Forcer l'activation de la révision et de la protection du format :

```bash
.\mdtx.exe docs --to Chinese --review true --guard true
```

Changer de modèle ou de style :

```bash
.\mdtx.exe README.md --to Chinese --model gpt-5-mini --tone technical
```

Produire des journaux détaillés pour faciliter le débogage :

```bash
.\mdtx.exe --verbose README.md --to Chinese
```

## ⚙️ Configuration

Le projet recherchera les fichiers de configuration selon l'ordre de priorité suivant :

1. `--config`Chemin spécifié par `--config`
2.  dans le répertoire racine du dépôt
3. `src/config.yaml`
4. `~/.mdtx/config.yaml`

Voici une configuration typique :

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
  # fast: 更快（不做review和guard）；balanced: 默认（按条件触发review和guard）；strict: 更严格（执行review和guard）。
  mode: balanced
  # 强制开启审校 Agent。关闭时，balanced/strict 仍可能按条件触发审校。
  enable_review: false
  # 强制开启格式修复 Agent。关闭时，balanced/strict 遇到校验失败仍可能触发修复。
  enable_format_guard: false
  # 输出校验失败时是否直接报错。
  fail_on_validation_error: true

# 分段策略。先按 Markdown 结构（标题/列表/表格/引用）打包，超长块再按行拆分。
segmentation:
  max_bundle_tokens: 3000
  min_bundle_tokens: 800

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

### Exemple de configuration de la clé API

Il est recommandé d'utiliser des variables d'environnement :

```powershell
$env:OPENAI_API_KEY="your-api-key"
.\mdtx.exe README.md --to Chinese
```

Peut également être écrit dans le fichier de configuration (non recommandé, présente des risques de sécurité) :

```yaml
provider:
  api_key: xxxxx
```

Si vous utilisez une interface compatible, vous pouvez également modifier dans `config.yaml` :

```yaml
provider:
  name: openai
  base_url: https://your-openai-compatible-endpoint/v1
  api_key_env: YOUR_API_KEY_ENV
  model: your-model-name
```

## 🔄 Flux d'exécution et mécanisme

Ce projet ne consiste pas à « donner tout le document Markdown au modèle pour traduction en une seule fois », mais plutôt en un pipeline plus robuste :

1. `MarkdownParser` Analyse d'abord le document source en AST pour identifier la structure Markdown
2. `SegmentExtractor` Extrait les segments traduisibles de l'AST et protège les contenus sensibles tels que les espaces réservés et la syntaxe de contrôle
3. `DocumentContextBuilder` Génère un résumé du document, des contraintes de style et un contexte terminologique
4. `Orchestrator` Organise les segments en plusieurs bundles selon la configuration, contrôle la taille de chaque appel au modèle
5. `TranslatorAgent` Traduit chaque bundle
6. `ReviewerAgent` effectue une révision conditionnelle dans les modes `balanced` / `strict`
7. `MarkdownRenderer` remappe les résultats de traduction vers l'AST et les rend au format Markdown
8. `MarkdownValidator` valide le front matter et la structure globale
9. Si la validation échoue, `FormatGuardAgent` tentera de corriger les problèmes de formatage si nécessaire
10. Génère en sortie le Markdown traduit et des fichiers de rapport optionnels

L'objectif de ce mécanisme est : préserver autant que possible l'apparence originale du Markdown, tout en garantissant que les résultats de traduction possèdent une cohérence contextuelle et une maintenabilité suffisantes. 🛡️

## 🗂️ Structure du projet

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

Autres fichiers importants dans le répertoire racine :

- `config.yaml` : Configuration exemple
- `requirements.txt` : Dépendances d'exécution
- `doc/` : README multilingue et documents de conception

## 🧪 Développement et tests

Installation des dépendances :

```bash
pip install -r requirements.txt
```

Si vous prévoyez de packager l'exécutable vous-même, vous aurez également besoin de :

```bash
pip install -r src/buildtool/requirements-build.txt
```

## Historique des stars

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
