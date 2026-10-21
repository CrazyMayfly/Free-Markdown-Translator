![مترجم-Markdown-مجاني](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

# مترجم Markdown مجاني

مترجم Markdown مجاني هو أداة ترجمة وثائق Markdown تعتمد على خط أنابيب وكيل الذكاء الاصطناعي (AI Agent)، يمكنها ترجمة وثائق Markdown إلى أي لغة، مع التركيز على الحفاظ على بنية Markdown الأصلية قدر الإمكان أثناء الترجمة، مع الحفاظ على تماسك الدلالة. إنها مناسبة لسيناريوهات مثل مواقع الوثائق، قواعد المعرفة المحلية، README، وثائق تقنية متعددة اللغات، إلخ. ✨

## 🚀 الميزات والخصائص الرئيسية

- 🧠 استخدام عملية ترجمة مدفوعة بالذكاء الاصطناعي بالإضافة إلى التحقق من صحة شجرة بناء الجملة (AST)، مما يحافظ على استقرار التنسيق واتساق السياق بشكل أكثر تماسكًا
- ✂️ يمكن تخصيص نمط اللغة، ومطابقة الإدخال، وتنسيق الإخراج، ودعم أوضاع ترجمة مختلفة (سريع، متوازن، صارم) لتناسب الاحتياجات المختلفة
- 🤖 مدمج `TranslatorAgent` و `ReviewerAgent` و `FormatGuardAgent`، المسؤولة عن الترجمة والمراجعة وإصلاح التنسيق (تم التمكين حسب وضع الترجمة)
- 🧱 يدعم حماية الهياكل مثل front matter، ومستويات العناوين، والقوائم، والجداول، وكتل التعليمات البرمجية، والروابط، إلخ
- ✅ يوفر التحقق من الصحة الهيكلية وتقارير الإخراج، للمساعدة في اكتشاف انحراف التنسيق وشذوذ المحتوى
- 🔌 متوافق مع واجهة نمط OpenAI، يمكن توصيله بـ OpenAI أو خدمات أخرى متوافقة
- ⚙️ يدعم لغات هدف متعددة، وترجمة مجلدات متكررة، ومعالجة متوازية، وقيود أسلوب الكتابة، والاحتفاظ بالمصطلحات

## ⚡ البداية السريعة

### الطريقة الأولى: التشغيل بعد استنساخ المستودع

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config
```

بعد التهيئة، سيتم إنشاء ملف الإعدادات الافتراضي في:

```text
~/.mdtx/config.yaml
```

بعد إعداد مفتاح API، يمكنك البدء في الترجمة:

```bash
python src/cli/main.py README.md --to english,japanese
```

### الطريقة الثانية: تنزيل ملف exe واستخدامه مباشرة

إذا كنت تستخدم Windows، يمكنك أيضًا تنزيل `mdtx.exe` المجمع جاهزًا وتشغيله مباشرة. يُنصح بتهيئة الإعدادات أولاً عند الاستخدام للمرة الأولى:

```powershell
.\mdtx.exe --init-config
```

ثم قم بتحرير:

```text
~/.mdtx/config.yaml
```

بعد اكتمال الإعداد، يمكنك التنفيذ:

```powershell
.\mdtx.exe README.md --to Chinese
```

### أمثلة على الأوامر للحالات الشائعة

ترجمة ملف واحد إلى الصينية:

```bash
.\mdtx.exe README.md --to Chinese
```

ترجمة مجلد `doc` بالكامل بشكل تكراري إلى الإنجليزية واليابانية:

```bash
.\mdtx.exe doc --to english,japanese
```

تحديد مجلد الإخراج:

```bash
.\mdtx.exe README.md --to Chinese --output translated
```

مطابقة ملفات Markdown ذات تنسيقات أسماء الملفات المحددة في الدليل فقط (باستخدام مطابقة التعابير النمطية):

```bash
.\mdtx.exe docs --to Chinese --match "name*.md"
```

زيادة التوازي، وتسريع الترجمة الضخمة:

```bash
.\mdtx.exe docs --to Chinese --threads 10
```

تفعيل عملية ترجمة وتحقق أكثر صرامة، تستهلك المزيد من الرموز (tokens)، وتستغرق وقتًا أطول ولكن تحصل على نتائج ترجمة أفضل:

```bash
.\mdtx.exe docs --to Chinese --mode quality
```

فرض تفعيل المراجعة وحماية التنسيق:

```bash
.\mdtx.exe docs --to Chinese --review true --guard true
```

تبديل النموذج أو أسلوب الكتابة:

```bash
.\mdtx.exe README.md --to Chinese --model gpt-5-mini --tone technical
```

إخراج سجلات مفصلة، لتسهيل استكشاف الأخطاء:

```bash
.\mdtx.exe --verbose README.md --to Chinese
```

## ⚙️ تعليمات التكوين

سيبحث المشروع عن ملفات التكوين حسب ترتيب الأولوية التالي:

1. `--config` المسار المحدد
2. في الدليل الجذر للمستودع `config.yaml`
3. `src/config.yaml`
4. `~/.mdtx/config.yaml`

إليك نموذج إعداد نموذجي:

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

### مثال على إعداد مفتاح API

يُوصى باستخدام متغيرات البيئة:

```powershell
$env:OPENAI_API_KEY="your-api-key"
.\mdtx.exe README.md --to Chinese
```

يمكن أيضًا كتابتها في ملف الإعدادات (غير موصى به، هناك مخاطر أمنية):

```yaml
provider:
  api_key: xxxxx
```

إذا كنت تستخدم واجهة متوافقة، يمكنك أيضًا التعديل في `config.yaml`:

```yaml
provider:
  name: openai
  base_url: https://your-openai-compatible-endpoint/v1
  api_key_env: YOUR_API_KEY_ENV
  model: your-model-name
```

## 🔄 سير العمل والآلية

هذا المشروع لا يقوم بـ «إلقاء ملف Markdown كامل مرة واحدة على النموذج للترجمة»، بل هو خط أنابيب أكثر أمانًا:

1. `MarkdownParser` قم أولاً بتحليل المستند المصدر إلى AST، والتعرف على بنية Markdown
2. `SegmentExtractor` استخرج الأجزاء القابلة للترجمة من AST، وقم بحماية العناصر الحساسة مثل العناصر النائبة وبناء الجملة التحكمي
3. `DocumentContextBuilder` قم بإنشاء ملخص المستند، وقيود الأسلوب، وسياق المصطلحات
4. `Orchestrator` قم بتنظيم الـ segment في حزم bundle متعددة وفقًا للإعدادات، للتحكم في حجم كل استدعاء للنموذج
5. `TranslatorAgent` قم بترجمة كل bundle
6. `ReviewerAgent` تُجري مراجعة مشروطة في وضع `balanced` / `quality`
7. `MarkdownRenderer` تعيد تعيين نتائج الترجمة إلى AST وتُظهرها بصيغة Markdown
8. `MarkdownValidator` تتحقق من صحة front matter والهيكل العام
9. إذا فشل التحقق، `FormatGuardAgent` تحاول إصلاح مشاكل التنسيق عند الضرورة
10. تُخرج أخيرًا ملف Markdown المترجم وملفات التقارير الاختيارية

هدف هذه الآلية هو: الحفاظ على مظهر Markdown الأصلي قدر الإمكان، مع ضمان اتساق السياق وقابلية الصيانة الكافية لنتائج الترجمة. 🛡️

## 🗂️ هيكل المشروع

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

ملفات مهمة أخرى في الدليل الجذري:

- `config.yaml`: تكوين مثال
- `requirements.txt`: تبعيات التشغيل
- `doc/`: مستندات README متعددة اللغات ومستندات التصميم

## 🧪 التطوير والاختبار

تثبيت التبعيات:

```bash
pip install -r requirements.txt
```

إذا كنت تخطط لحزم exe بنفسك، فستحتاج أيضًا إلى:

```bash
pip install -r src/buildtool/requirements-build.txt
```

## سجل النجوم

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
