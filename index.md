---
title: 如何使用Hugo搭建个人博客
slug: How to build a personal blog with Hugo
description: 本文介绍如何使用Hugo搭建个人博客以及注意事项
date: 2023-04-20T21:50:24+08:00
image: cover.webp
categories: ["技术"]
tags: ["blog", "Hugo"]
keywords: ["blog", "Hugo"]
toc: true
comments: true
readingTime: true
---

## 前言

最近几天刚入职实习，一是调整作息时间，二是适应工作，三是还有一些课程相关内容需要学习处理，实在不得闲。今天的作息时间终于调得差不多了，在处理完一些作业后，忙里偷闲写写博客。

写这个题目的原因也很简单，我前两天才将博客建好，趁热把一些经验以及踩坑写出来分享给大家。同样，许多人已经写过类似的话题了，我会直接把链接贴出来，而不会做机械式地重复。我会将我其中用到的知识整理出来分享。

## 参考链接

1. [The world’s fastest framework for building websites | Hugo (gohugo.io)](https://gohugo.io/)
2. [免费的个人博客系统搭建及部署解决方案（Hugo + GitHub Pages + Cusdis） · Pseudoyu](https://www.pseudoyu.com/zh/2022/03/24/free_blog_deploy_using_hugo_and_cusdis/)
3. [Hugo + GitHub Action，搭建你的博客自动发布系统 · Pseudoyu](https://www.pseudoyu.com/zh/2022/05/29/deploy_your_blog_using_hugo_and_github_action/)
4. [轻量级开源免费博客评论系统解决方案 （Cusdis + Railway） · Pseudoyu](https://www.pseudoyu.com/zh/2022/05/24/free_and_lightweight_blog_comment_system_using_cusdis_and_railway/)
5. [从零开始搭建一个免费的个人博客数据统计系统（umami + Vercel + Heroku） · Pseudoyu](https://www.pseudoyu.com/zh/2022/05/21/free_blog_analysis_using_umami_vercel_and_heroku/)
6. [个人网站的建立过程（一）：购买个人域名并配置动态域名解析 (jinli.cyou)](https://jinli.cyou/p/个人网站的建立过程一购买个人域名并配置动态域名解析/)
7. [个人网站的建立过程（二）：使用Hugo框架搭建个人网站 (jinli.cyou)](https://jinli.cyou/p/个人网站的建立过程二使用hugo框架搭建个人网站/)
8. [个人网站的建立过程（三）：Hugo主题stack的使用与优化 (jinli.cyou)](https://jinli.cyou/p/个人网站的建立过程三hugo主题stack的使用与优化/#语言转换按钮)
9. [个人网站的建立过程（四）：网站的搜索引擎优化（SEO） (jinli.cyou)](https://jinli.cyou/p/个人网站的建立过程四网站的搜索引擎优化seo/)

## 什么是Hugo？

### 静态页面生成器

其实，你要搭建个人博客的话看上面的链接已经足够。但我这里还是简单介绍一下必要的步骤。Hugo是一个静态页面生成器，它可以根据你的Markdown文本生和你选择的主题生成漂亮的静态页面。静态页面的好处是部署相对方便，响应速度快，坏处也很明显，你不能实时编辑页面，必须在本地编辑——生成页面——部署到服务器（当然也不是绝对的），而且难以集成一些传统前后端动态页面所拥有的功能；但即便这样，静态页面，或者说Hugo对个人来说也已经足够。

### Hugo的安装与使用

这部分很简单，直接照着官网的做就可以了[Quick Start | Hugo (gohugo.io)](https://gohugo.io/getting-started/quick-start/)，官网已经把下载hugo、设置主题、发布帖子等关键步骤以一种十分简单的教程给出来了。

**坑1**：如果你在Windows平台使用`winget install Hugo.Hugo.Extended`下载的hugo无法打开/正常使用的话，你需要到hugo 的安装目录把hugo.exe拷贝到你的博客文件夹里面，使用相对路径的形式运行hugo相关的指令，如`./hugo.exe server -D`，这样就能正常运行了

### Hugo主题的选择与安装

你可以到[Complete List | Hugo Themes (gohugo.io)](https://themes.gohugo.io/)浏览你自己喜欢的主题，当你想要使用一款主题时，你可以点击详情页的Demo查看这个主题的在线例子（部分主题没有Demo），点击Download下载该主题并使用（一般会跳转到Github仓库，其中有关于这个主题的详细信息）；然后你可以使用`git clone links position` 或者`git submodule add links positon`将该主题克隆到你的博客目录下；一般主题文件夹里都有一个exampleSite子文件夹，你可以使用该文件夹进行快速部署（注意保存你之前的配置文件）。如果你觉得你的主题跑起来和主题官网的示例差别很大的话，那大概率是你的问题，此时你应该检查你的目录名、文件名、文件头信息等。

![Hugo的Stack主题](image-20230420222917912.png)

## 使用`Github Action`自动发布博客

在讲自动发布之前，当然要先讲一下如何部署网站啦。

### 在服务器上部署网站

首先，使用`hugo --minify`生成网页静态文件（生成的目录为public），将`public`目录中的内容复制到你的服务器中（注意文件权限）；然后如下配置`nginx`代理（此处配置的是`https`，如果没有证书的话也可以配置`http`）

```
server {
        listen 443;
        server_name aprilme.love;
        # 证书
        ssl_certificate "/yourPath/aprilme.love.pem";
        # 私钥
        ssl_certificate_key "/yourPath/aprilme.love.key";
        location / {
        	# 此处是你刚刚复制到的目录
                root /yourpath/blog;
                   }
        }
```

这样，就可以在浏览器中键入你的域名来访问你的博客了。

你还可以通过如下配置将80端口的流量转发到443端口（也就是把`http`的流量转发到`https`），注意要把`aprilme.love`替换为你自己的域名。

```
server {
        listen 80;
        server_name aprilme.love;
        rewrite ^(.*)$ https://${server_name}$1;
                }
```

如果你没有证书的话，可以弄自签名证书（但浏览器会提示不安全，因为是自己签名，而不是权威机构签名的）；也可以去购买证书，不过目前的云服务器提供商都会免费送一些证书，这样直接去申请下载就好了，比如阿里云的服务器可以参考[2022阿里云免费SSL证书申请全过程（图文详解）-阿里云开发者社区 (aliyun.com)](https://developer.aliyun.com/article/875508)。

### 配置`Github Action`

你有没有发现，上面的部署过程虽然不难，但是每当你的博客内容有更新，你就要把文件复制来复制去的，十分麻烦。有没有一种方法，可以每当我们写好博客之后就自动发布，不需要我们手动发布呢？那当然是有的，就是使用`Github Action`.

#### `Github Action`是什么

`GitHub Actions`是GitHub平台提供的一种自动化工作流工具，用于在代码仓库中自动执行各种操作。它可以通过在仓库中配置和定义一系列事件触发的工作流程来帮助开发者自动化常见的软件开发任务，例如构建、测试、部署和通知等。

`GitHub Actions`允许开发者通过编写一些简单的YAML文件来定义工作流程，这些工作流程可以在特定的事件（例如代码推送、合并请求创建、标签发布等）发生时自动触发。工作流程中可以包含多个步骤（Actions），每个步骤可以执行一些特定的操作，例如运行命令、构建代码、运行测试、推送到其他代码仓库、发送通知等。

`GitHub Actions`提供了丰富的集成和生态系统，可以与许多其他开发工具和服务集成，例如Docker、AWS、Azure、Google Cloud、Slack、Jira等，从而实现更复杂的自动化工作流。

`GitHub Actions`可以帮助开发者提高开发效率、自动化重复性任务、确保代码质量，并促进团队协作。它是GitHub平台的一项强大的功能，广泛应用于开源项目和商业项目中。

#### `Github Action`的配置文件

在你的项目目录中创建`.github/workflows`文件夹，在该文件夹下创建`my_blog_deploy.yaml`文件，文件内容如下

```yaml
name: Deploy Hugo Project to Aliyun ECS

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v2

    - name: Setup Hugo
      uses: peaceiris/actions-hugo@v2
      with:
        hugo-version: 'latest'

    - name: Build Hugo Site
      run: hugo --minify

    - name: Deploy Site to Aliyun ECS
      uses: easingthemes/ssh-deploy@v2
      env:
        SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
        REMOTE_HOST: ${{ secrets.REMOTE_HOST }}
        REMOTE_USER: ${{ secrets.REMOTE_USER }}
        TARGET: /yourpath/blog
      with:
        source: public/
```

以下是该配置文件的解释：

1. `name`: 指定工作流的名称，这里命名为 "Deploy Hugo Project to Aliyun ECS"。
2. `on`: 指定触发工作流的事件，这里配置为在推送到 "main" 分支时触发工作流。
3. `jobs`: 定义一个或多个工作，这里定义了一个名为 "deploy" 的工作。
4. `runs-on`: 指定工作运行的操作系统环境，这里配置为 "ubuntu-latest"，表示在最新的 Ubuntu 环境中运行。
5. `steps`: 定义工作的一系列步骤。

- `name`: 指定每个步骤的名称，用于标识步骤的作用。
- `uses`: 指定使用的 Action，这里使用了多个不同的 Action 来执行不同的任务，例如使用 "actions/checkout@v2" Action 检出代码、使用 "peaceiris/actions-hugo@v2" Action 安装和配置 Hugo、使用 "easingthemes/ssh-deploy@v2" Action 部署网站到阿里云 ECS。
- `with`: 传递参数给使用的 Action，这里使用了不同的参数来配置 Hugo 的版本、设置部署目标的主机、用户和路径。
- `run`: 在当前工作环境中运行命令，这里使用 "hugo --minify" 命令构建 Hugo 网站并压缩输出。
- `env`: 设置环境变量，这里设置了用于 SSH 连接的私钥和远程主机、用户、目标路径的环境变量，这些值从 GitHub Secrets 中获取。

这个配置文件的目的是在每次推送到 "main" 分支时，自动构建 Hugo 网站并将生成的网站文件部署到阿里云 ECS 上指定的目录。这样可以实现持续集成和自动部署，提高开发效率并确保网站的最新版本在阿里云 ECS 上可用。

上面的`${{ secrets.REMOTE_HOST }}`是github仓库中的经过加密的环境变量，用于存储敏感信息，例如 API 密钥、私钥、密码等。以下是其设置方法

1. 打开 GitHub 仓库，在仓库页面的右上角点击 "Settings"。
2. 在仓库的 "Settings" 页面中，选择左侧菜单中的 "Secrets"。
3. 点击 "New repository secret" 按钮创建一个新的 Secrets。
4. 输入 Secrets 的名称和值，然后点击 "Add secret" 按钮保存。
5. 在GitHub Actions 的工作流程配置文件中，可以通过使用 `${{ secrets.SECRET_NAME }}` 的语法来引用 Secrets 的值

在之前的配置文件中，可以通过 `${{ secrets.SSH_PRIVATE_KEY }}`、`${{ secrets.REMOTE_HOST }}`、`${{ secrets.REMOTE_USER }}` 来获取对应的 Secrets 的值，这样这些敏感信息就可以安全地传递给相应的 GitHub Actions，用于进行部署等操作。

经过上面的配置后，每当你将代码push到仓库时，就会在`Github Action`提供的服务器中执行配置文件中的内容，然后通过`SSH`连接同步到你的服务器中，大概花费30s左右；这样就极大简化了人工操作，降低了复杂度。此外，`Github Action`还能干许多其他事情，功能十分强大！

## 集成评论系统

一个博客的评论系统的重要性不亚于其内容。选择一个自己喜欢的评论系统当然也很重要。以下是一些常见的评论系统

- [Artalk](https://artalk.js.org/)
- [Cactus](https://cactus.chat/)
- [Cusdis](https://cusdis.com/)
- [Disqus](https://disqus.com/)
- [DisqusJS](https://github.com/SukkaW/DisqusJS)
- [Giscus](https://giscus.app/)
- [Gitalk](https://github.com/gitalk/gitalk)
- [Remark42](https://remark42.com/)
- [Twikoo](https://twikoo.js.org/)
- [utterances](https://utteranc.es/)
- [Vssue](https://vssue.js.org/)
- [Waline](https://waline.js.org/)

我目前选择的是Cusdis，原因是

1. 开源和自托管：Cusdis 是一个开源的评论系统，你可以自行托管在自己的服务器上，拥有完全的数据控制权，不依赖于第三方服务。这意味着你可以保护用户的隐私，并且拥有自主管理和修改评论系统的能力。
2. 轻量级：Cusdis 的 SDK 只有 5kb（gzip 压缩后），相较于其他评论系统如 Disqus（24kb gzip 压缩后）来说，非常轻量级，不会给网站的加载速度带来太大的负担，有助于提升网站性能。
3. 不要求评论者登录：Cusdis 不要求评论者登录，评论者可以匿名发表评论，也不使用任何 cookies。这有助于减少用户的登录和注册门槛，提高用户参与度。
4. 易于使用：Cusdis 提供了一个简单的嵌入式评论工具，可以轻松地嵌入到网站的任何页面中，使用方便。
5. 邮件通知：Cusdis 支持邮件通知功能，让网站管理员能够及时收到新评论的通知，方便管理和回复评论。

关于Cusdis的部署相关内容官网和许多博客已经写得非常清楚了，我在这里主要说一下Cusdis的跨域问题。

### 解决Cusdis的跨域问题

在页面引用Cusdis的Embed Code的时候，容易发生**跨域**问题，无法加载js脚本或者评论数据。

```html
<div id="cusdis_thread"
  data-host="https://yourhost"
  data-app-id="yourid"
  data-page-id="{{ PAGE_ID }}"
  data-page-url="{{ PAGE_URL }}"
  data-page-title="{{ PAGE_TITLE }}"
></div>
<script async defer src="https://yourhost/js/cusdis.es.js"></script>
```

此时需要在nginx中添加响应头

`add_header 'Access-Control-Allow-Origin' 'yourhost';`

这样解决了无法加载js的问题，但在加载评论数据时又出现了问题：评论数据的响应头被加上了两个`'Access-Control-Allow-Origin' 'yourhost'`导致数据加载失败。

原因是在加载评论数据之前会先使用`Options`进行http请求，在之后的GET请求中nginx代理又给GET请求加上了一层`'Access-Control-Allow-Origin' 'yourhost'`，最终出现了跨域许可重复的问题。把Nginx的配置写成如下形式就可以完美解决跨域问题了。注意，为了安全性考虑，如果你的网站使用https，那么cusdis的host也必须使用https。

```
server {
        listen 443;
        ssl_certificate "your cert.pem";
        ssl_certificate_key "your cert.key";
        server_name yourhost;
        location / {
        proxy_pass http://127.0.0.1:3000;
        if ($uri !~* .*comments.*) {
        add_header 'Access-Control-Allow-Origin' '*';
        add_header 'Access-Control-Allow-Methods' 'GET, POST';
        add_header 'Access-Control-Allow-Headers' 'DNT,X-Mx-ReqToken,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,x-timezone-offset';}
        }}
```

## SEO，搜索引擎优化

已经有许多文章介绍过了如何在Google、Bing、Baidu上面进行搜索引擎优化的操作步骤，这部分我就不讲了。我来讲一下搜索引擎优化的相关知识。

### 搜索引擎的索引是什么

搜索引擎的索引是指搜索引擎在其数据库中保存的关于互联网上网页和内容的记录。搜索引擎通过抓取（或称为爬取、蜘蛛、抓取）互联网上的网页，并将其存储在自己的数据库中，以便用户在搜索时能够快速找到相关的网页。

搜索引擎的索引通常包含了大量的网页信息，包括网页的URL、标题、正文、链接、图片、视频等内容。搜索引擎通过对这些信息进行处理和索引，建立起一个结构化的数据库，用于存储和管理网页信息。

当用户在搜索引擎中输入关键词进行搜索时，搜索引擎会从自己的索引数据库中匹配关键词，并返回与之相关的网页结果。搜索引擎的索引质量和准确性对搜索结果的质量和准确性有着重要影响，因此搜索引擎公司会不断改进其索引算法和技术，以提供更好的搜索体验。

需要注意的是，不是所有的网页都被搜索引擎索引到，搜索引擎可能会根据其抓取和索引策略选择性地索引网页，并根据网页的质量、权威性、更新频率等因素进行排序和展示。因此，网站管理员可以通过一系列的搜索引擎优化（SEO）措施，提升自己网站被搜索引擎索引和排名的机会。

### 什么是SEO

SEO（Search Engine Optimization）即搜索引擎优化，是一种通过优化网站的内容、结构和技术，以提升网站在搜索引擎中的排名，从而增加网站在搜索结果页面上的可见性和流量的方法。SEO优化旨在使网站在搜索引擎中获得更高的有机（非付费）搜索排名，从而获得更多的有针对性的流量。

SEO优化通常包括以下几个方面的工作：

1. 关键词研究：通过研究用户在搜索引擎中使用的关键词，选择合适的关键词并将其应用到网站的内容中，从而使网站在与关键词相关的搜索中获得更高的排名。
2. 网站内容优化：优化网站的内容，包括标题、描述、正文等，使其更加有质量、有价值、有关联性，并符合搜索引擎的规范和要求。
3. 网站结构优化：优化网站的结构和布局，使其更加用户友好、易于导航和理解，并确保搜索引擎能够有效地抓取和索引网站的内容。
4. 网站技术优化：优化网站的技术方面，包括网站的加载速度、响应式设计、URL结构、页面标签等，以提升网站的用户体验和搜索引擎的爬取效果。
5. 外部链接建设：通过外部链接的建设，提升网站的链接权重和知名度，从而增加网站在搜索引擎中的权威性和可信度。
6. 社交媒体优化：通过在社交媒体平台上进行优化，包括分享网站内容、互动和参与社交媒体社区等，提升网站的曝光度和知名度。
7. 监测和分析：定期监测和分析网站的SEO效果，了解网站在搜索引擎中的排名和流量情况，并根据数据进行调整和优化。

SEO优化的目标是通过提升网站在搜索引擎中的排名，使其在用户搜索相关关键词时能够更容易地被找到，从而增加网站的有机流量，提升网站的品牌知名度和业务转化率。然而，SEO是一项长期而复杂的工作，需要不断的优化和持续的努力，同时也需要遵循搜索引擎的规范和要求，以确保网站能够持续地在搜索引擎中获得良好的排名。

### 什么是sitemap.xml

`sitemap.xml` 是一个用于网站的 XML 文件，其中包含了网站的结构化信息，用于通知搜索引擎网站的页面和内容的组织方式。它是一种用于搜索引擎优化（SEO）的技术，帮助搜索引擎更好地了解和索引网站的内容。

`sitemap.xml` 文件中通常包含了网站的所有页面的 URL 地址，以及这些页面的重要性、更新频率和最后更新时间等信息。搜索引擎可以通过读取 `sitemap.xml` 文件来了解网站的结构和内容，从而更加智能地抓取和索引网站的页面。

`sitemap.xml` 对于网站的 SEO 优化有以下几个作用：

1. 提升网站的索引效果：通过提交 `sitemap.xml` 文件给搜索引擎，可以帮助搜索引擎更全面地了解网站的内容，从而更好地进行索引和展示网站的页面。
2. 加快新页面的索引速度：当网站发布了新页面时，通过将新页面的 URL 添加到 `sitemap.xml` 文件中，并提交给搜索引擎，可以加快新页面被搜索引擎索引的速度。
3. 控制搜索引擎的抓取频率：通过在 `sitemap.xml` 文件中设置页面的更新频率和最后更新时间等信息，可以向搜索引擎提示页面的更新情况，从而帮助搜索引擎更加智能地抓取网站的页面。
4. 提升网站的用户体验：通过使用 `sitemap.xml` 文件，可以帮助搜索引擎更好地了解网站的结构和内容，从而提升用户在搜索引擎中找到和访问网站页面的体验。

## 使用Umami自建流量分析工具

前面使用的Google Analytics在国内加载慢，而且容易造成数据丢失，并且会将用户数据用于生成Google的用户画像。所以我选择了[Umami](https://umami.is/)作为替代品，在本地部署，更加的快捷轻便安全。

### Umami介绍

[Umami](https://umami.is/) 是一个简单易用、自托管的开源网站访问流量统计分析工具。Umami 不使用 Cookie，不跟踪用户，且所有收集的数据都会匿名化处理，符合 GDPR 政策，资源占用很低，虽然功能简单，但分析的数据内容很丰富，基本的来源国家，来源域名，使用的浏览器、系统、设备，访问的网页这些都有。还支持多国语言，完全可以用来替代 Google Analytics、Cloudflare Web Analytics、CNZZ、51LA 等统计工具，而且自己搭建也可以避免被 block 掉从而使统计数据更精确（**后来发现也会被部分去广告插件拦截…**）。[引用自[使用 Umami 自建网站流量统计分析工具 - atpX](https://atpx.com/blog/build-umami-web-analytics/)]

### 如何部署Umami

由于[umami官方文档](https://umami.is/docs)坏掉了，所以请移步至其[开源仓库](https://github.com/umami-software/umami)查看部署文档，一套操作下来还是很快的，在这里我来说一下容易遇到的问题。

首先在克隆Github仓库的时候`git clone https://github.com/umami-software/umami.git`容易出现网络问题，这时你可以将仓库先下载下来再解压到服务器的指定目录，你也可以将Github仓库复制到Gitee上，然后clone你的gitee仓库。但刚好gitee上存在一个[同步的仓库](https://gitee.com/873098424/umami/tree/master)，所以你可以将链接直接改为gitee仓库的[地址](https://gitee.com/873098424/umami/tree/master)，省去了很多麻烦。这时的命令为

```bash
git clone https://gitee.com/873098424/umami.git
```

然后继续跟着教程走。在你要`yarn build`之前，现在你的数据库中使用`CREATE DATABASE IF NOT EXISTS umami; `创建一个umami数据库，然后将配置文件的库名改为umami（与你创建的数据库名相同即可）。然后**不要去使用它提供的sql语句去创建表，因为在你启动后会自动创建表**。

之后，执行build，执行start（如果因为端口占用导致start失败，可以使用`yarn start --port=3001`来修改端口）。这样服务就算启动起来了。关于如何配置Nginx、登录、修改密码等，你可以参考这篇博客[使用 Umami 自建网站流量统计分析工具 - atpX](https://atpx.com/blog/build-umami-web-analytics/)。

至此，Umami应该可以正常使用了，如果控制台中提示该错误的`Failed to load resource: net::ERR_BLOCKED_BY_CLIENT`话，应该是被ADBlock等广告拦截器拦截了，你可以把你的广告拦截器关掉来解决，但是目前还没有找到能够避免广告拦截器拦截的好方法，所以数据可能不是那么准确。

## 总结

在阅读完以上内容后，我相信你对搭建自己的博客的基本流程已经较为熟悉了；**理解很重要，实践也一样重要**。在搭建个人博客的过程中间，由于环境、选择的主题、个人经验等不同，所碰到的问题肯定也各不相同。在这个过程中最重要的便是**耐心**，肯于花费时间去尝试解决所遇到的一个个问题，在学习中成长，在成长中学习。就如本文的封面一样，莫奈的睡莲，象征宁静、耐心。也预祝所有想要搭建自己的博客的同学，想要去实现自己目标的同学，虽然不可能所有事情都一番风顺，但只要拥有足够的耐心和能力，勇于去发现问题、解决问题，在自己不会的情况下求助外界，**定有所获，也必有所成。**
