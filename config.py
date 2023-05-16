# ssl._create_default_https_context = ssl._create_unverified_context
# 控制是否在文章前面添加机器翻译的Warning
insert_warnings = True
# 配置目标语言及其warning，默认按照定义顺序翻译为下面语言
warnings_mapping = {
    'zh-tw': "警告：本文由機器翻譯生成，可能導致質量不佳或信息有誤，請謹慎閱讀！",
    'en': 'Warning: This page is translated by MACHINE, which may lead to POOR QUALITY or INCORRECT INFORMATION, please read with CAUTION!',
    'ja': '警告: この記事は機械翻訳されているため、品質が低かったり不正確な情報が含まれる可能性があります。よくお読みください。',
    # 西班牙语
    'es': 'Advertencia: este artículo está traducido por una máquina, lo que puede dar lugar a una mala calidad o información incorrecta. ¡Lea atentamente!',
    # 俄语
    'ru': 'Предупреждение: Эта статья переведена автоматически, что может привести к некачественной или неверной информации, пожалуйста, внимательно прочитайте!',
    # 法语
    'fr': 'Attention : cet article est traduit par machine, ce qui peut entraîner une mauvaise qualité ou des informations incorrectes, veuillez lire attentivement !',
    # 德语
    'de': 'Achtung: Dieser Artikel wurde maschinell übersetzt, was zu schlechter Qualität oder falschen Informationen führen kann, bitte sorgfältig lesen!',
    # 印地语
    'hi': 'चेतावनी: यह लेख मशीन द्वारा अनुवादित है, जिससे खराब गुणवत्ता या गलत जानकारी हो सकती है, कृपया ध्यान से पढ़ें!',
    # 葡萄牙语
    'pt': 'Aviso: Este artigo é traduzido por máquina, o que pode levar a má qualidade ou informações incorretas, leia com atenção!',
    # 韩语
    'ko': '경고: 이 기사는 기계 번역으로 생성되어 품질이 좋지 않거나 잘못된 정보로 이어질 수 있으므로 주의 깊게 읽으십시오!'
}

# 指定要跳过翻译的字符，分别为加粗符号、在``中的非中文字符，`，换行符
skipped_regexs = [r"\*\*。?", r'#+', r'`[^\u4E00-\u9FFF]*?`', r'`', r'"[^\u4E00-\u9FFF]*?"', r'Hello World',
                 '\n']
# pattern = "|".join(map(re.escape, self.skipped_chars))
pattern = "({})".format("|".join(skipped_regexs))
# 文件目录下需要翻译的文档的名称
detect_filenames = ['index', 'readme', '_index']
# markdown中Front Matter不用翻译的部分
front_matter_transparent_keys = ('date:', 'slug:', 'toc', 'image', 'comments', 'readingTime', 'menu:', '    main:',
                                 '        weight:', '        params:', '            icon:', 'links:',
                                 '    website:', '    image:', 'layout:', 'outputs:', '    - html', '    - json',
                                 'license:', '#', 'style:', '    background:', '    color:')
# 需要以Key-Value形式翻译的部分
front_matter_key_value_keys = ('title:', 'description:', '        name:', '  - title:', '    description:')
# 以Key-Value—Arrays形式翻译
front_matter_key_value_array_keys = ('tags:', 'categories:', 'keywords:')
