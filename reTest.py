import re

pattern = r'\[.*?\]\(.*?\)'
sample = '由于[umami官方文档](https://umami.is/docs)坏掉了，所以请移步至其[开源仓库](https://github.com/umami-software/umami)查看部署文档，一套操作下来还是很快的，在这里我来说一下容易遇到的问题。'
sample = '[Umami](https://umami.is/) 是一个简单易用、自托管的开源网站访问流量统计分析工具。Umami 不使用 Cookie，不跟踪用户，且所有收集的数据都会匿名化处理，符合 GDPR 政策，资源占用很低，虽然功能简单，但分析的数据内容很丰富，基本的来源国家，来源域名，使用的浏览器、系统、设备，访问的网页这些都有。还支持多国语言，完全可以用来替代 Google Analytics、Cloudflare Web Analytics、CNZZ、51LA 等统计工具，而且自己搭建也可以避免被 block 掉从而使统计数据更精确（**后来发现也会被部分去广告插件拦截…**）。[引用自[使用 Umami 自建网站流量统计分析工具 - atpX](https://atpx.com/blog/build-umami-web-analytics/)]'
sample = '1. [如何在Ubuntu 20.04配置SSH密钥免密码登录](https://www.myfreax.com/how-to-set-up-ssh-keys-on-ubuntu-20-04/)\n'
sample_img = '由于![umami官方文档](https://umami.is/docs)坏掉了，所以请移步至其[开源仓库](https://github.com/umami-software/umami)查看部署文档，一套操作下来还是很快的，在这里我来说一下容易遇到的问题。'

p = re.compile(pattern)
text = p.split(sample)
links = re.findall(pattern, sample)
print(text)
print(links)
#
# print(re.search(pattern, sample))
# print('\n'.join(['a', 'b', 'c']).split('\n'))
