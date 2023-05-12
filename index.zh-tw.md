---
title: 如何使用Hugo搭建個人博客
slug: How to build a personal blog with Hugo
description: 本文介紹如何使用Hugo搭建個人博客以及注意事項
date: 2023-04-20T21:50:24+08:00
image: cover.webp
categories: ["技術"]
tags: ["blog", "Hugo"]
keywords: ["blog", "Hugo"]
toc: true
comments: true
readingTime: true
---
> 警告：本文由機器翻譯生成，可能導致質量不佳或信息有誤，請謹慎閱讀！
## 前言

最近幾天剛入職實習，一是調整作息時間，二是適應工作，三是還有一些課程相關內容需要學習處理，實在不得閒。今天的作息時間終於調得差不多了，在處理完一些作業後，忙裡偷閒寫寫博客。

寫這個題目的原因也很簡單，我前兩天才將博客建好，趁熱把一些經驗以及踩坑寫出來分享給大家。同樣，許多人已經寫過類似的話題了，我會直接把鏈接貼出來，而不會做機械式地重複。我會將我其中用到的知識整理出來分享。

## 參考鏈接

1. [The world’s fastest framework for building websites | Hugo (gohugo.io)](https://gohugo.io)
2. [免費的個人博客系統搭建及部署解決方案（Hugo + GitHub Pages + Cusdis） · Pseudoyu](https://www.pseudoyu.com/zh/2022/03/24/free_blog_deploy_using_hugo_and_cusdis)
3. [Hugo + GitHub Action，搭建你的博客自動發布系統 · Pseudoyu](https://www.pseudoyu.com/zh/2022/05/29/deploy_your_blog_using_hugo_and_github_action)
4. [輕量級開源免費博客評論系統解決方案 （Cusdis + Railway） · Pseudoyu](https://www.pseudoyu.com/zh/2022/05/24/free_and_lightweight_blog_comment_system_using_cusdis_and_railway)
5. [從零開始搭建一個免費的個人博客數據統計系統（umami + Vercel + Heroku） · Pseudoyu](https://www.pseudoyu.com/zh/2022/05/21/free_blog_analysis_using_umami_vercel_and_heroku)
6. [個人網站的建立過程（一）：購買個人域名並配置動態域名解析 (jinli.cyou)](https://jinli.cyou/p/个人网站的建立过程一购买个人域名并配置动态域名解析)
7. [個人網站的建立過程（二）：使用Hugo框架搭建個人網站 (jinli.cyou)](https://jinli.cyou/p/个人网站的建立过程二使用hugo框架搭建个人网站)
8. [個人網站的建立過程（三）：Hugo主題stack的使用與優化 (jinli.cyou)](https://jinli.cyou/p/个人网站的建立过程三hugo主题stack的使用与优化/#语言转换按)
9. [個人網站的建立過程（四）：網站的搜索引擎優化（SEO） (jinli.cyou)](https://jinli.cyou/p/个人网站的建立过程四网站的搜索引擎优化seo)

## 什麼是Hugo？

### 靜態頁面生成器

其實，你要搭建個人博客的話看上面的鏈接已經足夠。但我這裡還是簡單介紹一下必要的步驟。 Hugo是一個靜態頁面生成器，它可以根據你的Markdown文本生和你選擇的主題生成漂亮的靜態頁面。靜態頁面的好處是部署相對方便，響應速度快，壞處也很明顯，你不能實時編輯頁面，必須在本地編輯——生成頁面——部署到服務器（當然也不是絕對的），而且難以集成一些傳統前後端動態頁面所擁有的功能；但即便這樣，靜態頁面，或者說Hugo對個人來說也已經足夠。

### Hugo的安裝與使用

這部分很簡單，直接照著官網的做就可以了[Quick Start | Hugo (gohugo.io)](https://gohugo.io/getting-started/quick-start)，官網已經把下載hugo、設置主題、發布帖子等關鍵步驟以一種十分簡單的教程給出來了。

**坑1**：如果你在Windows平台使用`winget install Hugo.Hugo.Extended`下載的hugo無法打開/正常使用的話，你需要到hugo 的安裝目錄把hugo.exe拷貝到你的博客文件夾裡面，使用相對路徑的形式運行hugo相關的指令，如`./hugo.exe server -D`，這樣就能正常運行了

### Hugo主題的選擇與安裝

你可以到[Complete List | Hugo Themes (gohugo.io)](https://themes.gohugo.io)瀏覽你自己喜歡的主題，當你想要使用一款主題時，你可以點擊詳情頁的Demo查看這個主題的在線例子（部分主題沒有Demo），點擊Download下載該主題並使用（一般會跳轉到Github倉庫，其中有關於這個主題的詳細信息）；然後你可以使用`git clone links position` 或者`git submodule add links positon`將該主題克隆到你的博客目錄下；一般主題文件夾裡都有一個exampleSite子文件夾，你可以使用該文件夾進行快速部署（注意保存你之前的配置文件）。如果你覺得你的主題跑起來和主題官網的示例差別很大的話，那大概率是你的問題，此時你應該檢查你的目錄名、文件名、文件頭信息等。

![Hugo的Stack主題](image-20230420222917912.png)
## 使用`Github Action`自動發布博客

在講自動發布之前，當然要先講一下如何部署網站啦。

### 在服務器上部署網站

首先，使用`hugo --minify`生成網頁靜態文件（生成的目錄為public），將`public`目錄中的內容複製到你的服務器中（注意文件權限）；然後如下配置`nginx`代理（此處配置的是`https`，如果沒有證書的話也可以配置`http`）

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

這樣，就可以在瀏覽器中鍵入你的域名來訪問你的博客了。

你還可以通過如下配置將80端口的流量轉發到443端口（也就是把`http`的流量轉發到`https`），注意要把`aprilme.love`替換為你自己的域名。

```
server {
        listen 80;
        server_name aprilme.love;
        rewrite ^(.*)$ https://${server_name}$1;
                }
```

如果你沒有證書的話，可以弄自簽名證書（但瀏覽器會提示不安全，因為是自己簽名，而不是權威機構簽名的）；也可以去購買證書，不過目前的雲服務器提供商都會免費送一些證書，這樣直接去申請下載就好了，比如阿里雲的服務器可以參考[2022阿里雲免費SSL證書申請全過程（圖文詳解）-阿里雲開發者社區 (aliyun.com)](https://developer.aliyun.com/article/87550)。

### 配置`Github Action`

你有沒有發現，上面的部署過程雖然不難，但是每當你的博客內容有更新，你就要把文件複製來複製去的，十分麻煩。有沒有一種方法，可以每當我們寫好博客之後就自動發布，不需要我們手動發布呢？那當然是有的，就是使用`Github Action`.

#### `Github Action`是什麼

`GitHub Actions`是GitHub平台提供的一種自動化工作流工具，用於在代碼倉庫中自動執行各種操作。它可以通過在倉庫中配置和定義一系列事件觸發的工作流程來幫助開發者自動化常見的軟件開發任務，例如構建、測試、部署和通知等。

`GitHub Actions`允許開發者通過編寫一些簡單的YAML文件來定義工作流程，這些工作流程可以在特定的事件（例如代碼推送、合併請求創建、標籤發布等）發生時自動觸發。工作流程中可以包含多個步驟（Actions），每個步驟可以執行一些特定的操作，例如運行命令、構建代碼、運行測試、推送到其他代碼倉庫、發送通知等。

`GitHub Actions`提供了豐富的集成和生態系統，可以與許多其他開發工具和服務集成，例如Docker、AWS、Azure、Google Cloud、Slack、Jira等，從而實現更複雜的自動化工作流。

`GitHub Actions`可以幫助開發者提高開發效率、自動化重複性任務、確保代碼質量，並促進團隊協作。它是GitHub平台的一項強大的功能，廣泛應用於開源項目和商業項目中。

#### `Github Action`的配置文件

在你的項目目錄中創建`.github/workflows`文件夾，在該文件夾下創建`my_blog_deploy.yaml`文件，文件內容如下

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

以下是該配置文件的解釋：

1. `name`: 指定工作流的名稱，這裡命名為 "Deploy Hugo Project to Aliyun ECS"。
2. `on`: 指定觸發工作流的事件，這裡配置為在推送到 "main" 分支時觸發工作流。
3. `jobs`: 定義一個或多個工作，這裡定義了一個名為 "deploy" 的工作。
4. `runs-on`: 指定工作運行的操作系統環境，這裡配置為 "ubuntu-latest"，表示在最新的 Ubuntu 環境中運行。
5. `steps`: 定義工作的一系列步驟。

- `name`: 指定每個步驟的名稱，用於標識步驟的作用。
- `uses`: 指定使用的 Action，這裡使用了多個不同的 Action 來執行不同的任務，例如使用 "actions/checkout@v2" Action 檢出代碼、使用 "peaceiris/actions-hugo@v2" Action 安裝和配置 Hugo、使用 "easingthemes/ssh-deploy@v2" Action 部署網站到阿里雲 ECS。
- `with`: 傳遞參數給使用的 Action，這裡使用了不同的參數來配置 Hugo 的版本、設置部署目標的主機、用戶和路徑。
- `run`: 在當前工作環境中運行命令，這裡使用 "hugo --minify" 命令構建 Hugo 網站並壓縮輸出。
- `env`: 設置環境變量，這裡設置了用於 SSH 連接的私鑰和遠程主機、用戶、目標路徑的環境變量，這些值從 GitHub Secrets 中獲取。

這個配置文件的目的是在每次推送到 "main" 分支時，自動構建 Hugo 網站並將生成的網站文件部署到阿里雲 ECS 上指定的目錄。這樣可以實現持續集成和自動部署，提高開發效率並確保網站的最新版本在阿里雲 ECS 上可用。

上面的`${{ secrets.REMOTE_HOST }}`是github倉庫中的經過加密的環境變量，用於存儲敏感信息，例如 API 密鑰、私鑰、密碼等。以下是其設置方法

1. 打開 GitHub 倉庫，在倉庫頁面的右上角點擊 "Settings"。
2. 在倉庫的 "Settings" 頁面中，選擇左側菜單中的 "Secrets"。
3. 點擊 "New repository secret" 按鈕創建一個新的 Secrets。
4. 輸入 Secrets 的名稱和值，然後點擊 "Add secret" 按鈕保存。
5. 在GitHub Actions 的工作流程配置文件中，可以通過使用 `${{ secrets.SECRET_NAME }}` 的語法來引用 Secrets 的值

在之前的配置文件中，可以通過 `${{ secrets.SSH_PRIVATE_KEY }}`、`${{ secrets.REMOTE_HOST }}`、`${{ secrets.REMOTE_USER }}` 來獲取對應的 Secrets 的值，這樣這些敏感信息就可以安全地傳遞給相應的 GitHub Actions，用於進行部署等操作。

經過上面的配置後，每當你將代碼push到倉庫時，就會在`Github Action`提供的服務器中執行配置文件中的內容，然後通過`SSH`連接同步到你的服務器中，大概花費30s左右；這樣就極大簡化了人工操作，降低了複雜度。此外，`Github Action`還能幹許多其他事情，功能十分強大！

## 集成評論系統

一個博客的評論系統的重要性不亞於其內容。選擇一個自己喜歡的評論系統當然也很重要。以下是一些常見的評論系統

- [Artalk](https://artalk.js.org)
- [Cactus](https://cactus.chat)
- [Cusdis](https://cusdis.com)
- [Disqus](https://disqus.com)
- [DisqusJS](https://github.com/SukkaW/DisqusJ)
- [Giscus](https://giscus.app)
- [Gitalk](https://github.com/gitalk/gital)
- [Remark42](https://remark42.com)
- [Twikoo](https://twikoo.js.org)
- [utterances](https://utteranc.es)
- [Vssue](https://vssue.js.org)
- [Waline](https://waline.js.org)

我目前選擇的是Cusdis，原因是

1. 開源和自託管：Cusdis 是一個開源的評論系統，你可以自行託管在自己的服務器上，擁有完全的數據控制權，不依賴於第三方服務。這意味著你可以保護用戶的隱私，並且擁有自主管理和修改評論系統的能力。
2. 輕量級：Cusdis 的 SDK 只有 5kb（gzip 壓縮後），相較於其他評論系統如 Disqus（24kb gzip 壓縮後）來說，非常輕量級，不會給網站的加載速度帶來太大的負擔，有助於提升網站性能。
3. 不要求評論者登錄：Cusdis 不要求評論者登錄，評論者可以匿名發表評論，也不使用任何 cookies。這有助於減少用戶的登錄和註冊門檻，提高用戶參與度。
4. 易於使用：Cusdis 提供了一個簡單的嵌入式評論工具，可以輕鬆地嵌入到網站的任何頁面中，使用方便。
5. 郵件通知：Cusdis 支持郵件通知功能，讓網站管理員能夠及時收到新評論的通知，方便管理和回複評論。

關於Cusdis的部署相關內容官網和許多博客已經寫得非常清楚了，我在這裡主要說一下Cusdis的跨域問題。

### 解決Cusdis的跨域問題

在頁面引用Cusdis的Embed Code的時候，容易發生**跨域**問題，無法加載js腳本或者評論數據。

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

此時需要在nginx中添加響應頭

`add_header 'Access-Control-Allow-Origin' 'yourhost';`

這樣解決了無法加載js的問題，但在加載評論數據時又出現了問題：評論數據的響應頭被加上了兩個`'Access-Control-Allow-Origin' 'yourhost'`導致數據加載失敗。

原因是在加載評論數據之前會先使用`Options`進行http請求，在之後的GET請求中nginx代理又給GET請求加上了一層`'Access-Control-Allow-Origin' 'yourhost'`，最終出現了跨域許可重複的問題。把Nginx的配置寫成如下形式就可以完美解決跨域問題了。注意，為了安全性考慮，如果你的網站使用https，那麼cusdis的host也必須使用https。

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

## SEO，搜索引擎優化

已經有許多文章介紹過瞭如何在Google、Bing、Baidu上面進行搜索引擎優化的操作步驟，這部分我就不講了。我來講一下搜索引擎優化的相關知識。

### 搜索引擎的索引是什麼

搜索引擎的索引是指搜索引擎在其數據庫中保存的關於互聯網上網頁和內容的記錄。搜索引擎通過抓取（或稱為爬取、蜘蛛、抓取）互聯網上的網頁，並將其存儲在自己的數據庫中，以便用戶在搜索時能夠快速找到相關的網頁。

搜索引擎的索引通常包含了大量的網頁信息，包括網頁的URL、標題、正文、鏈接、圖片、視頻等內容。搜索引擎通過對這些信息進行處理和索引，建立起一個結構化的數據庫，用於存儲和管理網頁信息。

當用戶在搜索引擎中輸入關鍵詞進行搜索時，搜索引擎會從自己的索引數據庫中匹配關鍵詞，並返回與之相關的網頁結果。搜索引擎的索引質量和準確性對搜索結果的質量和準確性有著重要影響，因此搜索引擎公司會不斷改進其索引算法和技術，以提供更好的搜索體驗。

需要注意的是，不是所有的網頁都被搜索引擎索引到，搜索引擎可能會根據其抓取和索引策略選擇性地索引網頁，並根據網頁的質量、權威性、更新頻率等因素進行排序和展示。因此，網站管理員可以通過一系列的搜索引擎優化（SEO）措施，提升自己網站被搜索引擎索引和排名的機會。

### 什麼是SEO

SEO（Search Engine Optimization）即搜索引擎優化，是一種通過優化網站的內容、結構和技術，以提升網站在搜索引擎中的排名，從而增加網站在搜索結果頁面上的可見性和流量的方法。 SEO優化旨在使網站在搜索引擎中獲得更高的有機（非付費）搜索排名，從而獲得更多的有針對性的流量。

SEO優化通常包括以下幾個方面的工作：

1. 關鍵詞研究：通過研究用戶在搜索引擎中使用的關鍵詞，選擇合適的關鍵詞並將其應用到網站的內容中，從而使網站在與關鍵詞相關的搜索中獲得更高的排名。
2. 網站內容優化：優化網站的內容，包括標題、描述、正文等，使其更加有質量、有價值、有關聯性，並符合搜索引擎的規範和要求。
3. 網站結構優化：優化網站的結構和佈局，使其更加用戶友好、易於導航和理解，並確保搜索引擎能夠有效地抓取和索引網站的內容。
4. 網站技術優化：優化網站的技術方面，包括網站的加載速度、響應式設計、URL結構、頁面標籤等，以提升網站的用戶體驗和搜索引擎的爬取效果。
5. 外部鏈接建設：通過外部鏈接的建設，提升網站的鏈接權重和知名度，從而增加網站在搜索引擎中的權威性和可信度。
6. 社交媒體優化：通過在社交媒體平台上進行優化，包括分享網站內容、互動和參與社交媒體社區等，提升網站的曝光度和知名度。
7. 監測和分析：定期監測和分析網站的SEO效果，了解網站在搜索引擎中的排名和流量情況，並根據數據進行調整和優化。

SEO優化的目標是通過提升網站在搜索引擎中的排名，使其在用戶搜索相關關鍵詞時能夠更容易地被找到，從而增加網站的有機流量，提升網站的品牌知名度和業務轉化率。然而，SEO是一項長期而復雜的工作，需要不斷的優化和持續的努力，同時也需要遵循搜索引擎的規範和要求，以確保網站能夠持續地在搜索引擎中獲得良好的排名。

### 什麼是sitemap.xml

`sitemap.xml` 是一個用於網站的 XML 文件，其中包含了網站的結構化信息，用於通知搜索引擎網站的頁面和內容的組織方式。它是一種用於搜索引擎優化（SEO）的技術，幫助搜索引擎更好地了解和索引網站的內容。

`sitemap.xml` 文件中通常包含了網站的所有頁面的 URL 地址，以及這些頁面的重要性、更新頻率和最後更新時間等信息。搜索引擎可以通過讀取 `sitemap.xml` 文件來了解網站的結構和內容，從而更加智能地抓取和索引網站的頁面。

`sitemap.xml` 對於網站的 SEO 優化有以下幾個作用：

1. 提升網站的索引效果：通過提交 `sitemap.xml` 文件給搜索引擎，可以幫助搜索引擎更全面地了解網站的內容，從而更好地進行索引和展示網站的頁面。
2. 加快新頁面的索引速度：當網站發布了新頁面時，通過將新頁面的 URL 添加到 `sitemap.xml` 文件中，並提交給搜索引擎，可以加快新頁面被搜索引擎索引的速度。
3. 控制搜索引擎的抓取頻率：通過在 `sitemap.xml` 文件中設置頁面的更新頻率和最後更新時間等信息，可以向搜索引擎提示頁面的更新情況，從而幫助搜索引擎更加智能地抓取網站的頁面。
4. 提升網站的用戶體驗：通過使用 `sitemap.xml` 文件，可以幫助搜索引擎更好地了解網站的結構和內容，從而提升用戶在搜索引擎中找到和訪問網站頁面的體驗。

## 使用Umami自建流量分析工具

前面使用的Google Analytics在國內加載慢，而且容易造成數據丟失，並且會將用戶數據用於生成Google的用戶畫像。所以我選擇了[Umami](https://umami.is)作為替代品，在本地部署，更加的快捷輕便安全。

### Umami介紹

[Umami](https://umami.is) 是一個簡單易用、自託管的開源網站訪問流量統計分析工具。 Umami 不使用 Cookie，不跟踪用戶，且所有收集的數據都會匿名化處理，符合 GDPR 政策，資源佔用很低，雖然功能簡單，但分析的數據內容很豐富，基本的來源國家，來源域名，使用的瀏覽器、系統、設備，訪問的網頁這些都有。還支持多國語言，完全可以用來替代 Google Analytics、Cloudflare Web Analytics、CNZZ、51LA 等統計工具，而且自己搭建也可以避免被 block 掉從而使統計數據更精確（**後來發現也會被部分去廣告插件攔截…**）。[引用自[使用 Umami 自建網站流量統計分析工具 - atpX](https://atpx.com/blog/build-umami-web-analytics)]

### 如何部署Umami

由於[umami官方文檔](https://umami.is/doc)壞掉了，所以請移步至其[開源倉庫](https://github.com/umami-software/umam)查看部署文檔，一套操作下來還是很快的，在這裡我來說一下容易遇到的問題。

首先在克隆Github倉庫的時候`git clone https://github.com/umami-software/umami.git`容易出現網絡問題，這時你可以將倉庫先下載下來再解壓到服務器的指定目錄，你也可以將Github倉庫複製到Gitee上，然後clone你的gitee倉庫。但剛好gitee上存在一個[同步的倉庫](https://gitee.com/873098424/umami/tree/maste)，所以你可以將鏈接直接改為gitee倉庫的[地址](https://gitee.com/873098424/umami/tree/maste)，省去了很多麻煩。這時的命令為

```bash
git clone https://gitee.com/873098424/umami.git
```

然後繼續跟著教程走。在你要`yarn build`之前，現在你的數據庫中使用`CREATE DATABASE IF NOT EXISTS umami; `創建一個umami數據庫，然後將配置文件的庫名改為umami（與你創建的數據庫名相同即可）。然後**不要去使用它提供的sql語句去創建表，因為在你啟動後會自動創建表**。

之後，執行build，執行start（如果因為端口占用導致start失敗，可以使用`yarn start --port=3001`來修改端口）。這樣服務就算啟動起來了。關於如何配置Nginx、登錄、修改密碼等，你可以參考這篇博客[使用 Umami 自建網站流量統計分析工具 - atpX](https://atpx.com/blog/build-umami-web-analytics)。

至此，Umami應該可以正常使用了，如果控制台中提示該錯誤的`Failed to load resource: net::ERR_BLOCKED_BY_CLIENT`話，應該是被ADBlock等廣告攔截器攔截了，你可以把你的廣告攔截器關掉來解決，但是目前還沒有找到能夠避免廣告攔截器攔截的好方法，所以數據可能不是那麼準確。

## 總結

在閱讀完以上內容後，我相信你對搭建自己的博客的基本流程已經較為熟悉了；**理解很重要，實踐也一樣重要**。在搭建個人博客的過程中間，由於環境、選擇的主題、個人經驗等不同，所碰到的問題肯定也各不相同。在這個過程中最重要的便是**耐心**，肯於花費時間去嘗試解決所遇到的一個個問題，在學習中成長，在成長中學習。就如本文的封面一樣，莫奈的睡蓮，象徵寧靜、耐心。也預祝所有想要搭建自己的博客的同學，想要去實現自己目標的同學，雖然不可能所有事情都一番風順，但只要擁有足夠的耐心和能力，勇於去發現問題、解決問題，在自己不會的情況下求助外界，**定有所獲，也必有所成。 **
