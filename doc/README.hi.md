# नि: शुल्क मार्कडाउन अनुवादक

> चेतावनी: यह लेख मशीन द्वारा अनुवादित है, जिससे खराब गुणवत्ता या गलत जानकारी हो सकती है, कृपया ध्यान से पढ़ें!


[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

## संक्षिप्त परिचय

मुफ्त मार्कडाउन अनुवादक एक पर आधारित है [अनुवादकों](https://github.com/UlionTse/translators) फ्री और ओपन सोर्स मार्कडाउन डॉक्यूमेंट ट्रांसलेटर आपके मार्कडाउन डॉक्यूमेंट को किसी भी प्रकार की भाषा में अनुवाद कर सकता है।

समारोह:

- किसी भी प्रकार की भाषा में मार्कडाउन दस्तावेज़ का अनुवाद करें
- समर्थन में विभिन्न प्रकार के अनुवाद इंजन शामिल हैं जैसे कि Google, बिंग, अलीबाबा, SOGOU, Youdao, Tencent, Baidu और अन्य अनुवाद इंजन
- मूल रूप से, यह मार्कडाउन दस्तावेज़ के मूल प्रारूप को नष्ट नहीं करेगा
- समवर्ती अनुवाद का समर्थन करें
- एक फ़ोल्डर के तहत कई फ़ोल्डर और कई फ़ाइलों का समर्थन करें, जो विशिष्ट दृश्यों के लिए बहुत सुविधाजनक है
- मशीन अनुवाद के मार्कडाउन दस्तावेज़ में चेतावनी जोड़ने के लिए समर्थन

इस कार्यक्रम के लिए संदर्भ [संपूर्ण मार्कडाउन दस्तावेज़, V2 संशोधित संस्करण (nightli.com) का अनुवाद करने के लिए अनुवाद करने के लिए अनुवाद।](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/)

## स्थापना और प्रचालन

ध्यान दें कि यदि आप Google अनुवाद और अन्य अनुवाद इंजनों का उपयोग करते हैं, जिन्होंने मुख्य भूमि चीन में सेवाएं प्रदान नहीं की हैं, तो आपको सामान्य रूप से उपयोग करने के लिए मुख्य भूमि चीन और अन्य क्षेत्रों में एजेंटों को जोड़ने की आवश्यकता हो सकती है।

निष्पादन योग्य कार्यक्रम एक ही निर्देशिका के तहत एक ही निर्देशिका का उपयोग करता है `config.yaml` फ़ाइल का उपयोग कॉन्फ़िगरेशन फ़ाइल के रूप में किया जाता है, चाहिए `config.yaml` कमी होने पर, डिफ़ॉल्ट कॉन्फ़िगरेशन, कॉन्फ़िगरेशन विवरण का उपयोग करें, अनुभाग की सामग्री को देखें।

1. दाईं ओर रिलीज संस्करण डाउनलोड करें
2. विघटन के बाद, स्टार्टअप प्रोग्राम को डबल करें, और फिर अनुवाद के लिए मार्कडाउन दस्तावेज़ या फ़ोल्डर के मार्ग का मार्ग टाइप करें
3. या अनुवाद करने के लिए कंसोल में कमांड का उपयोग करें

```bash
usage: MarkdownTranslator.exe [-h] [-f file/folder [file/folder ...]]

Markdown translator, which translates markdown documents to target languages
you want.

options:
  -h, --help            show this help message and exit
  -f file/folder [file/folder ...]
                        the markdown documents or folders to translate.
```

फ़ाइलों या फ़ोल्डरों को पैरामीटर स्थिति में अनुवादित करने के लिए रखें, आप कई फ़ोल्डर जोड़ सकते हैं, और प्रोग्राम स्वचालित रूप से प्रत्येक फ़ोल्डर में कॉन्फ़िगरेशन फ़ाइल में निर्दिष्ट फ़ाइलों में से प्रत्येक का अनुवाद करेगा।

उदाहरण के लिए, यदि निर्दिष्ट लक्ष्य भाषा अंग्रेजी (एन), जापानी (जेए) है, तो `readme.md` फ़ाइल को उसी फ़ोल्डर में अनुवादित किया जाएगा `readme.en.md`,`readme.ja.md` सार

## विन्यास

कृपया निष्पादन योग्य कार्यक्रम के समान निर्देशिका का उपयोग करें `config.yaml` विन्यास, संबंधित `yaml` पाठ प्रारूप के निर्देशों को संदर्भित किया जा सकता है:[यमल क्या है?](https://www.redhat.com/en/topics/automation/what-is-yaml)

1. `insert_warnings`: नियंत्रित करें कि क्या दस्तावेज़ के सामने मशीन द्वारा अनुवादित चेतावनियों को जोड़ना है

2. `src_language`: स्रोत भाषा निर्दिष्ट करें, ऑटो इंगित करता है कि Google स्वचालित रूप से पहचान करता है

3. `warnings_mapping`: इसी भाषा की विशिष्ट सामग्री को मशीन अनुवाद चेतावनी द्वारा अनुवादित किया गया है

4. `target_langs`: लक्ष्य भाषा जिसका अनुवाद करने की आवश्यकता है

5. `src_filenames`: मार्कडाउन दस्तावेज़ का नाम जिसे फ़ाइल निर्देशिका में स्वचालित रूप से पता लगाने और अनुवादित करने की आवश्यकता है

6. `compact_langs`: कॉम्पैक्ट भाषा, अंग्रेजी जैसी गैर -कॉम्पैक्ट भाषा के पृथक्करण को हल करना

7. `front_matter_transparent_keys`: मार्कडाउन के सामने के मामले को भागों का अनुवाद करने की आवश्यकता नहीं है

8. `front_matter_key_value_keys`: कुंजी-मूल्य के रूप में अनुवाद के भाग का फ्रंट मैटर हिस्सा

9. `front_matter_key_value_array_keys`: कुंजी-मूल्य-र्रेज़ के रूप में फ्रंट मैटर ट्रांसलेशन

उदाहरण कॉन्फ़िगरेशन फ़ाइल:

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

### लक्ष्य भाषा कॉन्फ़िगरेशन विवरण

लक्ष्य भाषा को आईएसओ 639-1 भाषा कोड का उपयोग करने की आवश्यकता है। [आईएसओ 639-1 कोड की सूची -wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes), यहाँ कुछ आमतौर पर उपयोग किए जाने वाले भाषा कोड हैं

|भाषा का नाम|यह भाषा दावा करती है|भाषा कोड|
| ---------- | ------------------------------ | -------- |
|चीनी|चीनी, चीनी, चीनी|जांचा|
|अंग्रेज़ी|अंग्रेज़ी|एन|
|जापानी|जापानी|जा|
|स्पैनिश|एस्पानोल|तों|
|रूसी|बेरंग|आरयू|
|फ्रांसीसी|फ्रांसिस|फादर|
|जर्मन|deutsch|डे|
|अरबी|बेरंग|एआर|
|हिंदी|बेरंग|नमस्ते|
|पुर्तगाली|पुर्तगुग|पोटी|
|कोरियाई|/कोरियाई, उत्तर कोरिया 말/조선말|कू|