![Free-Markdown-Translator](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

# फ्री मार्कडाउन अनुवादक

फ्री मार्कडाउन अनुवादक एक AI एजेंट पाइपलाइन पर आधारित मार्कडाउन दस्तावेज़ अनुवादक उपकरण है, जो मार्कडाउन दस्तावेज़ों को किसी भी भाषा में अनुवादित कर सकता है, अनुवाद प्रक्रिया के दौरान मूल मार्कडाउन संरचना को बनाए रखने और साथ ही अर्थपूर्ण सुसंगतता बनाए रखने पर केंद्रित है। यह दस्तावेज़ साइटों, स्थानीय ज्ञान आधार, README, बहुभाषी तकनीकी दस्तावेज़ों आदि जैसे परिदृश्यों के लिए उपयुक्त है। ✨

## 🚀 मुख्य विशेषताएं और सुविधाएं

- 🧠 AI-संचालित अनुवाद प्रक्रिया और AST सिंटैक्स ट्री सत्यापन का उपयोग करता है, जो प्रारूप स्थिरता और अधिक सुसंगत संदर्भ स्थिरता बनाए रख सकता है
- ✂️ भाषा शैली, इनपुट मिलान, आउटपुट प्रारूप को अनुकूलित किया जा सकता है, विभिन्न आवश्यकताओं के अनुकूल होने के लिए विभिन्न अनुवाद मोड (त्वरित, संतुलित, सख्त) का समर्थन करता है
- 🤖 बिल्ट-इन `TranslatorAgent`, `ReviewerAgent`, `FormatGuardAgent`, क्रमशः अनुवाद, समीक्षा और प्रारूप मरम्मत के लिए जिम्मेदार (अनुवाद मोड के अनुसार सक्षम)
- 🧱 front matter, शीर्षक स्तर, सूचियां, तालिकाएं, कोड ब्लॉक, लिंक आदि संरचनाओं के संरक्षण का समर्थन करता है
- ✅ संरचना सत्यापन और आउटपुट रिपोर्ट प्रदान करता है, प्रारूप ड्रिफ्ट और सामग्री विसंगतियों को खोजने में मदद करता है
- 🔌 OpenAI शैली इंटरफेस के साथ संगत, OpenAI या अन्य संगत सेवाओं से जुड़ सकता है
- ⚙️ बहु-लक्ष्य भाषाओं, डायरेक्टरी पुनरावर्ती अनुवाद, समानांतर प्रोसेसिंग, शैली बाधाओं और शब्दावली संरक्षण का समर्थन करता है

## ⚡ त्वरित प्रारंभ

### विधि एक: रिपॉजिटरी क्लोन करने के बाद शुरू करें

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config
```

प्रारंभिकीकरण के बाद, डिफ़ॉल्ट कॉन्फ़िगरेशन फ़ाइल यहाँ जनरेट होगी:

```text
~/.mdtx/config.yaml
```

API Key कॉन्फ़िगर करने के बाद आप अनुवाद शुरू कर सकते हैं:

```bash
python src/cli/main.py README.md --to english,japanese
```

### विधि दो: exe डाउनलोड करें और सीधे उपयोग करें

यदि आप Windows का उपयोग कर रहे हैं, तो आप पैकेज किया हुआ `mdtx.exe` डाउनलोड करके सीधे चला सकते हैं। पहली बार उपयोग करने पर कॉन्फ़िगरेशन प्रारंभिकीकरण करने की सलाह दी जाती है:

```powershell
.\mdtx.exe --init-config
```

फिर संपादित करें:

```text
~/.mdtx/config.yaml
```

कॉन्फ़िगरेशन पूरा होने के बाद आप निष्पादित कर सकते हैं:

```powershell
.\mdtx.exe README.md --to Chinese
```

### सामान्य परिदृश्य कमांड उदाहरण

एकल फ़ाइल का चीनी भाषा में अनुवाद करें:

```bash
.\mdtx.exe README.md --to Chinese
```

पूरे `doc` डायरेक्टरी को अंग्रेजी और जापानी में पुनरावर्ती रूप से अनुवादित करें:

```bash
.\mdtx.exe doc --to english,japanese
```

आउटपुट डायरेक्टरी निर्दिष्ट करें:

```bash
.\mdtx.exe README.md --to Chinese --output translated
```

केवल डायरेक्टरी में निर्दिष्ट फ़ाइल नाम प्रारूप वाले Markdown फ़ाइलों का मिलान करें (रेगुलर एक्सप्रेशन मिलान का उपयोग करें):

```bash
.\mdtx.exe docs --to Chinese --match "name*.md"
```

समानांतरता बढ़ाएं, बड़े पैमाने पर अनुवाद को तेज करें:

```bash
.\mdtx.exe docs --to Chinese --threads 10
```

सख्त अनुवाद और सत्यापन प्रक्रिया सक्षम करें, अधिक टोकन खपत होती है, अधिक समय लगता है लेकिन बेहतर अनुवाद परिणाम मिलते हैं:

```bash
.\mdtx.exe docs --to Chinese --mode strict
```

प्रूफरीडिंग और प्रारूप सुरक्षा को बलपूर्वक सक्षम करें:

```bash
.\mdtx.exe docs --to Chinese --review true --guard true
```

मॉडल या शैली बदलें:

```bash
.\mdtx.exe README.md --to Chinese --model gpt-5-mini --tone technical
```

विस्तृत लॉग आउटपुट करें, समस्या निवारण के लिए सुविधाजनक:

```bash
.\mdtx.exe --verbose README.md --to Chinese
```

## ⚙️ कॉन्फ़िगरेशन विवरण

परियोजना निम्नलिखित प्राथमिकता क्रम में कॉन्फ़िगरेशन फ़ाइलों की खोज करेगी:

1. `--config` द्वारा निर्दिष्ट पथ
2.  रिपॉजिटरी रूट डायरेक्टरी के तहत `config.yaml`
3. `src/config.yaml`
4. `~/.mdtx/config.yaml`

एक विशिष्ट कॉन्फ़िगरेशन इस प्रकार है:

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

### API Key कॉन्फ़िगरेशन उदाहरण

पर्यावरण चर (environment variables) का उपयोग करने की अनुशंसा की जाती है:

```powershell
$env:OPENAI_API_KEY="your-api-key"
.\mdtx.exe README.md --to Chinese
```

इसे कॉन्फ़िगरेशन फ़ाइल में भी लिखा जा सकता है (अनुशंसित नहीं, सुरक्षा जोखिम मौजूद है):

```yaml
provider:
  api_key: xxxxx
```

यदि आप संगत इंटरफ़ेस का उपयोग करते हैं, तो आप `config.yaml` में भी संशोधन कर सकते हैं:

```yaml
provider:
  name: openai
  base_url: https://your-openai-compatible-endpoint/v1
  api_key_env: YOUR_API_KEY_ENV
  model: your-model-name
```

## 🔄 निष्पादन प्रवाह और तंत्र

यह परियोजना "पूरे Markdown को एक बार में मॉडल को अनुवाद के लिए सौंपना" नहीं है, बल्कि एक अधिक विश्वसनीय पाइपलाइन है:

1. `MarkdownParser` पहले स्रोत दस्तावेज़ को AST में पार्स करें, Markdown संरचना की पहचान करें
2. `SegmentExtractor` AST से अनुवाद योग्य खंड निकालें, और प्लेसहोल्डर, नियंत्रण सिंटैक्स आदि संवेदनशील सामग्री की सुरक्षा करें
3. `DocumentContextBuilder` दस्तावेज़ सारांश, शैली बाधाएं, शब्दावली संदर्भ उत्पन्न करें
4. `Orchestrator` कॉन्फ़िगरेशन के अनुसार segment को कई bundle में व्यवस्थित करें, प्रत्येक मॉडल कॉल के आकार को नियंत्रित करें
5. `TranslatorAgent` प्रत्येक bundle का अनुवाद करें
6. `ReviewerAgent` `balanced` / `strict` मोड में शर्तों के आधार पर समीक्षा करता है
7. `MarkdownRenderer` अनुवाद परिणामों को वापस AST में मैप करता है और Markdown के रूप में रेंडर करता है
8. `MarkdownValidator` front matter और समग्र संरचना को सत्यापित करता है
9. यदि सत्यापन विफल होता है, तो `FormatGuardAgent` आवश्यकता पड़ने पर प्रारूप समस्याओं को ठीक करने का प्रयास करता है
10. अंत में अनुवादित Markdown और वैकल्पिक रिपोर्ट फ़ाइलें आउटपुट करता है

इस तंत्र का लक्ष्य है: यथासंभव Markdown के मूल स्वरूप को बनाए रखना, जबकि अनुवाद परिणामों में पर्याप्त संदर्भ स्थिरता और रखरखाव क्षमता सुनिश्चित करना। 🛡️

## 🗂️ परियोजना संरचना

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

रूट डायरेक्टरी में अन्य महत्वपूर्ण फ़ाइलें:

- `config.yaml`: उदाहरण कॉन्फ़िगरेशन
- `requirements.txt`: रनटाइम निर्भरताएं
- `doc/`: बहुभाषी README और डिज़ाइन दस्तावेज़

## 🧪 विकास और परीक्षण

डिपेंडेंसी इंस्टॉल करें:

```bash
pip install -r requirements.txt
```

यदि आप स्वयं exe पैकेज करने की तैयारी कर रहे हैं, तो आपको इनकी भी आवश्यकता होगी:

```bash
pip install -r src/buildtool/requirements-build.txt
```

## स्टार हिस्ट्री

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
