---
title: How to use HUGO to build a personal blog
slug: How to build a personal blog with Hugo
description: This article introduces how to use HUGO to build personal blogs and precautions
date: 2023-04-20T21:50:24+08:00
image: cover.webp
categories: ["technology"]
tags: ["blog", "Hugo"]
keywords: ["blog", "Hugo"]
toc: true
comments: true
Readingtime: true
---
> Warning: This article is translated by machine, which may lead to poor quality or incorrect information, please read with caution!
## Foreword

In recent days, I just joined the internship. One is to adjust the schedule, the other is to adapt to the work, and the third is that there are some courses related content that needs to be learned and processed. Today's schedule is finally almost adjusted. After handling some homework, I am busy writing blogs.

The reason for writing this topic is also very simple. I just built my blog two days ago, and wrote some experiences and step on the pit to share with everyone. Similarly, many people have already written similar topics, and I will directly paste the link without repeating mechanically. I will sort out the knowledge I used in it.

## Reference link

1. [The World ’s FASEST FRAMEWORK for Building Websites | Hugo (Gohugo.io)](https://gohugo.io)
2. [Free personal blogging system building and deployment solution (hugo + github pays + cusdis) · PSEUDOYU](https://www.pseudoyu.com/zh/2022/03/24/free_blog_deploy_using_hugo_and_cusdis)
3..[Hugo + github action, build your blog automatic release system · PSEUDOYU](https://www.pseudoyu.com/zh/2022/05/29/deploy_your_blog_using_hugo_and_github_action)
4. 4..[Lightweight open source free blog review system solution (CUSDIS + RAILWAY) · Pseudoyu](https://www.pseudoyu.com/zh/2022/05/24/free_and_lightweight_blog_comment_system_using_cusdis_and_railway)
5.[Establish a free personal blog data statistics system (UMAMI + VERCEL + Heroku) · PSEUDOYU](https://www.pseudoyu.com/zh/2022/05/21/free_blog_analysis_using_umami_vercel_and_heroku)
6.[Establishment process of personal website (1): Purchase personal domain name and configure dynamic domain name analysis (jinli.cyou)](https://jinli.cyou/p/个人网站的建立过程一购买个人域名并配置动态域名解析)
7.[The establishment of a personal website (2): Use the Hugo framework to build a personal website (Jinli.cyou)](https://jinli.cyou/p/个人网站的建立过程二使用hugo框架搭建个人网站)
8. [The establishment process of a personal website (3): The use and optimization of the hugo theme stack (Jinli.Cyou)](https://jinli.cyou/p/个人网站的建立过程三hugo主题stack的使用与优化/#语言转换按)
9. [Establishment process of personal website (4): Site search engine optimization (SEO) (jinli.cyou)](https://jinli.cyou/p/个人网站的建立过程四网站的搜索引擎优化seo)

## What is hugo?

### Static page generator

In fact, if you want to build a personal blog, it is enough to look at the link above. But I still briefly introduce the necessary steps. Hugo is a static page generator. It can generate beautiful static pages based on your Markdown text student and the theme you choose. The advantage of the static page is that the deployment is relatively convenient, the response speed is fast, and the disadvantage is obvious. You cannot edit the page in real time. You must edit the page -deploy to the server (of course not absolute), and it is difficult to integrate some traditional traditions The functions of the front and back dynamic pages; but even so, the static page, or HUGO is enough for individuals.

### HUGO's installation and use

This part is very simple, just do it directly on the official website[Quick Start | Hugo (Gohugo.io)](https://gohugo.io/getting-started/quick-start)The official website has given the key steps for downloading HUGO, setting themes, and posting posts. It has been given a very simple tutorial.

** Pit 1 **: If you use the `Wing Install hugo.hugo.extended` to download the hugo on the Windows platform, if you need to copy the hugo.exe to your blog folder to the hugo installation directory to the hugo installation directory. Inside, run HUGO -related instructions in the form of relative paths, such as `./hugo.exe server -d`, so that it can run normally

### HUGO theme selection and installation

You can arrive[Complete List | Hugo themes (Gohugo.io)](https://themes.gohugo.io)Browse your favorite theme. When you want to use a theme, you can click DEMO of the details page to view the online example (some themes do not have DEMO). GitHub warehouse, which is about this theme detailed information); then you can use the `git clone links posity` or` git submodule addls positon` to clone the theme to your blog directory; ExampleSite subfolder, you can use the folder for fast deployment (note that you preserve your previous configuration file). If you think that your theme is very different from the example of the theme official website, then the probability is your problem. At this time, you should check your directory name, file name, file header information, etc. at this time.

![Hugo's stack theme](image-20230420222917912.png)
## Use `github action` to automatically release blogs

Before talking about automatic release, of course, let's talk about how to deploy the website.

### Deploy a website on the server

First of all, use the `hugo -minify` to generate web static files (the generated directory is public), copy the content in the` public` directory to your server (pay attention to file permissions); then configure the following `nginx` agent (here The configuration is `https`, if there is no certificate, you can also configure` http`))

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

In this way, you can type your domain name in your browser to visit your blog.

You can also forward the flow of port 80 to port 443 by the following configuration (that is, to forward the traffic of `http` to` https`). Pay attention to replace the `Aprilme.love` with your own domain name.

```
server {
        listen 80;
        server_name aprilme.love;
        rewrite ^(.*)$ https://${server_name}$1;
                }
```

If you do not have a certificate, you can get a signature certificate (but the browser will indicate that it is not safe because it is signed by your own, not the signature of an authoritative agency); you can also buy a certificate, but the current cloud server provider will send some free to some free to send some for free Certificate, just go to apply for download directly. For example, Alibaba Cloud's server can refer to[2022 Alibaba Cloud Free SSL Certificate Application (Detailed Explanation of Graphic) -Eriyun Developer Community (Aliyun.com)](https://developer.aliyun.com/article/87550)Essence

### Configuration `github action`

Have you found that although the above deployment process is not difficult, but whenever your blog content is updated, you need to copy the file to copy it, which is very troublesome. Is there a way to release it automatically when we write a blog. We don't need to manually publish it? Of course there are, using `github action`.

#### `GitHub Action`

`Github Actions` is an automated workflow tool provided by the GitHub platform to automatically perform various operations in the code warehouse. It can help developers automatically automate software development tasks by configuration and defining a series of event triggers in the warehouse, such as building, testing, deployment, and notifications.

`Github Actions` allows developers to define the workflow by writing some simple YAML files. These workflows can be automatically triggered when specific events (such as code push, consolidated request creation, label release, etc.). The workflow can contain multiple steps (Acts), each step can perform some specific operations, such as running commands, constructing code, running tests, pushing to other code warehouses, sending notifications, etc.

`Github Actions` provides rich integration and ecosystems that can integrate with many other development tools and services, such as Docker, AWS, Azure, Google Cloud, Slack, Jira, etc., thereby achieving more complex automation workflows.

`Github Actions` can help developers improve development efficiency, automate repetitive tasks, ensure the quality of code, and promote teamwork. It is a powerful feature of the Github platform, which is widely used in open source projects and commercial projects.

#### `Github Action`

Create `.github/Workflows` folders in your project directory, create` my_blog_deploy.yaml` files under the folder, the content of the file is as follows

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

The following is the explanation of the configuration file:

1. `name`: specify the name of the workflow, which is named" Deploy Hugo Project to Aliyun ECS ".
2. On`: Specify events that trigger the workflow, which is configured here to trigger the workflow when pushing to the "main" branch.
3. Jobs`: Define one or more jobs, which defines a job called "deploy".
4. `Runs-on`: Specify the operating system environment of the work operation. Here is" Ubuntu-Latest ", which means running in the latest Ubuntu environment.
5. Steps`: a series of steps to define work.

-` name`: Specify the name of each step to identify the step of the step.
-`users`: specified Action used. Here you use multiple different ACTION to perform different tasks, such as using" Actions/Checkout@v2 "action to detect code, use" Peaceiris/Actions-Hugo@v2 "action installation. And configure hugo, deploy the website of "Easingthemes/SSH-DEPLOY@v2" Action to Alibaba Cloud ECS.
-` With`: The Action used to pass the parameter to the use, here use different parameters to configure the HUGO version, setting up the hosting target, users, and paths.
-` Run`: Run commands in the current working environment. Here is the "HUGO -Minify" command to build a Hugo website and compress the output.
-`ENV`: Set up environmental variables. Here is a private key and remote host, user, and target path for SSH connection. These values ​​are obtained from Github Secrets.

The purpose of this configuration file is to automatically build the HUGO website and deploy the generated website files to the designated directory specified on Alibaba Cloud ECS when each pushing to the "Main" branch. This can achieve continuous integration and automatic deployment, improve development efficiency and ensure that the latest version of the website is available on Alibaba Cloud ECS.

The above `$ {secrets.remote_host}` is an encrypted environment variable in the github warehouse, which is used to store sensitive information, such as API key, private key, password, etc. The following is its setting method

1. Open the github warehouse and click "Settings" in the upper right corner of the warehouse page.
2. In the "Settings" page of the warehouse, select "Secrets" in the left menu.
3. Click the "New Repository Secret" button to create a new Secrets.
4. Enter the name and value of the Secrets, and then click the "Add Secret" button to save.
5. In the work flow configuration file of GitHub Actions, you can use the syntax of the Secrets

In the previous configuration file, you can use `$ {secrets.ssh_private_key}`, `$ {{Secrets.remote_host}`, `$ {{Secrets.remote_user}}` `to get the corresponding selects Value, this way These sensitive information can be safely passed to the corresponding GitHub Actions for deployment and other operations.

After the above configuration, whenever you put the code push to the warehouse, you will execute the content in the configuration file in the server provided by the `GitHub Action` Right and right; this greatly simplifies artificial operations and reduces complexity. In addition, `Github Action` can do many other things, and the function is very powerful!

## Integrated review system

The importance of a blog review system is no less important than its content. It is also important to choose a comment system you like. Here are some common comment systems

- [Artalk](https://artalk.js.org)
- [Cactus](https://cactus.chat)
- [Cusdis](https://cusdis.com)
- [Disqu](https://disqus.com)
- [Disqusjs](https://github.com/SukkaW/DisqusJ)
- [Giscus](https://giscus.app)
- [Gitalk](https://github.com/gitalk/gital)
- [Remark42](https://remark42.com)
- [Twikoo](https://twikoo.js.org)
- [utterant](https://utteranc.es)
- [Vssue](https://vssue.js.org)
- [Waline](https://waline.js.org)

What I currently choose is cusdis, the reason is

1. Open source and self -hosting: CUSDIS is an open source review system. You can host it on your own server. It has complete data control and does not depend on third -party services. This means that you can protect the privacy of users and have the ability to independently manage and modify the comment system.
2. Lightweight: CUSDIS's SDK is only 5KB (after GZIP compression). Compared with other comment systems such as Disqus (after 24KB GZIP compression), it is very lightweight and will not bring much to the loading speed of the website too much. The burden helps improve the performance of the website.
3. Do not require commentators to log in: CUSDIS does not require commentators to log in. Commentary can anonymous comments without using any cookies. This helps reduce user login and registration threshold and increase user participation.
4. Easy to use: CUSDIS provides a simple embedded comment tool that can be easily embedded in any page of the website, which is convenient to use.
5. Email notification: CUSDIS supports mail notification functions, allowing website administrators to receive new comment notifications in time to facilitate management and recovery comments.

The official website and many blogs of the deployment of CUSDIS have been written very clearly. I will mainly talk about CUSDIS's cross -domain issues here.

### Solve the cross -domain problem of CUSDIS

When the page references the Embed Code of CUSDIS, it is prone to ** cross -domain ** problems, and JS scripts or comment data cannot be loaded.

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

At this time, you need to add a response head to nginx

`add_header 'access-control-allow-origin' 'yourhost';`

This solves the problem that cannot be loaded, but there is a problem when loading the comment data: the response header of the comment data is added with two `` Access-Control-Allow-Origin '' Yourhost'` to lead to the failure of the data loading.

The reason is that the HTTP request will be used to use the `Options` to make the HTTP request before loading the comment data. In the later GET request, the nginx agent adds a layer of the GET request. Repeat the cross -domain license. Write the configuration of Nginx into the following form to perfectly solve cross -domain problems. Note that for security considerations, if your website uses HTTPS, then the host of CUSDIS must also use HTTPS.

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

## SEO, search engine optimization

Many articles have introduced how to optimize the operation steps of search engine optimization on Google, Bing, and Baidu. I won't talk about this part. Let me talk about the relevant knowledge of search engine optimization.

### What is the index of search engine

The index of search engine refers to the records of search engines on the Internet and content preserved in its database. Search engines on the Internet on the Internet by grabbing (or crawling, spiders, and crawling) are stored in their own database so that users can quickly find related web pages when searching.

The index of search engines usually contain a large amount of web information, including the URL, title, text, links, pictures, videos, etc. of the webpage. Search engines process and index through this information to establish a structured database for storing and managing webpage information.

When users enter keywords in the search engine for search, the search engine will match the keywords from their index database and return the results related to the webpage. The index quality and accuracy of search engines have an important impact on the quality and accuracy of the search results. Therefore, search engine companies will continuously improve their index algorithms and technologies to provide a better search experience.

It should be noted that not all web pages are indeed by search engines. Search engines may selectively index web pages based on their capture and index strategies, and sort and display according to factors such as the quality, authority, and update frequency of the webpage. Essence Therefore, the website administrator can improve the opportunity to index and rank their website through a series of search engine optimization (SEO) measures.

### What is SEO

Seo (Search Engine Optimization) is the search engine optimization. It is a method of optimizing the content of the website in the search engine through the content, structure and technology of optimizing the website, thereby increasing the visibility and traffic of the website on the search results page. The SEO optimization aims to enable the website to get higher organic (non -paid) search rankings in search engines, so as to get more targeted traffic.

SEO optimization usually includes the following aspects:

1. Keyword research: By studying the keywords used by the user in the search engine, select the appropriate keywords and apply it to the content of the website, so that the website gets higher rankings in search of keywords.
2. Website content optimization: Optimize the content of the website, including title, description, text, etc., making it more quality, valuable, related to associate, and meet the specifications and requirements of search engines.
3. Website structure optimization: Optimize the structure and layout of the website to make it more user -friendly, easy to navigate and understand, and ensure that search engines can effectively grasp the content of the website.
4. Website technology optimization: Optimize the technology of the website, including the loading speed of the website, the response design, the URL structure, the page label, etc., to improve the user experience of the website and the crawling effect of search engines.
5. External link construction: Through the construction of external links to increase the link weight and popularity of the website, thereby increasing the authority and credibility of the website in the search engine.
6. Social media optimization: Optimized through social media platforms, including sharing website content, interaction and participation in social media communities, etc., to enhance the exposure and popularity of the website.
7. Monitoring and analysis: Regularly monitor and analyze the SEO effect of the website, understand the ranking and traffic of the website in the search engine, and adjust and optimize it based on the data.

The goal of SEO optimization is to improve the ranking of the website in the search engine to make it easier to find when users search for related keywords, thereby increasing the organic traffic of the website and increasing the brand awareness and business conversion rate of the website. However, SEO is a long -term and complex work that needs to be continuously optimized and continuous efforts. At the same time, it also needs to follow the specifications and requirements of search engines to ensure that the website can continue to get a good ranking in search engines.

### What is sitemap.xml

`sitemap.xml` is an XML file used for the website, which contains the structured information of the website to notify the pages and content of the search engine website. It is a technology for search engine optimization (SEO) to help search engines better understand and index websites.

The `sitemap.xml` file usually contains the URL address of all pages of the website, as well as information such as the importance of these pages, update frequency, and final update time. Search engines can understand the structure and content of the website by reading the `sitemap.xml` file, so as to intelligently capture and index the page of the website.

`sitemap.xml` has the following functions for the SEO optimization of the website:

1. Improve the indexing effect of the website: By submitting the `sitemap.xml` file to the search engine, it can help search engines understand the content of the website more comprehensive, so as to better index and display the page of the website.
2. Accelerate the indexing speed of the new page: When the website releases a new page, by adding the URL of the new page to the `sitemap.xml` file, and submitting it to the search engine, it can speed up the speed of the new page being indexed by the search engine.
3. Control the frequency of grabbing the search engine: By setting the update frequency and final update time of the page in the `sitemap.xml` file, the update of the search engine prompt page can help the search engine to intelligently grab more intelligent grabbing more intelligently The page of the website.
4. Improve the user experience of the website: By using the `sitemap.xml` file, you can help search engines better understand the structure and content of the website, thereby enhancing users to find and access the website page experience in search engines.

## Using UMAMI self -built flow analysis tool

The previous Google Analytics used in China slowly, and it is easy to cause data loss. It will also use user data to generate Google user portraits. So I chose[Umami](https://umami.is)As a substitute, deployment in the local area is more fast and safe.

### UMAMI introduction

[Umami](https://umami.is) It is a simple and easy -to -use open source website access traffic statistics analysis tool. UMAMI does not use cookies, does not track users, and all collected data will be processed anonymously, which is in line with the GDPR policy. The resources are very low. Although the function is simple, the analysis data is very rich. Browser, system, equipment, web pages visited. It also supports multi -language, which can be used to replace Google Analytics, Cloudflare Web Analytics, CNZZ, 51LA and other statistical tools, and it can also be avoided by BLOCK to make statistical data more accurate (** later found that it will be partially advertising. Plug -in interception ... **).[Quote from [Umami self -built website traffic statistics analysis tool -ATPX](https://atpx.com/blog/build-umami-web-analytics)]

### How to deploy UMAMI

because[UMAMI official documentation](https://umami.is/doc)It's broken, so please move to it[Open source warehouse](https://github.com/umami-software/umam)Check the deployment document, and the operation is still very fast. Here I will talk about the problems that are easy to encounter.

First of all, when the cloned github warehouse `git clone https:// github.com/umami-software/umami.git` is easy to occur. At this time, you can download the warehouse first and decompress it to the designated directory of the server, and you also You can copy the github warehouse to the Gitee, and then clone your Gitee warehouse. But there is just one on Gitee[Synchronous warehouse](https://gitee.com/873098424/umami/tree/maste)So you can directly change the link to the Gitee warehouse[address](https://gitee.com/873098424/umami/tree/maste), Save a lot of trouble. The command at this time is

```bash
git clone https://gitee.com/873098424/umami.git
```

Then continue to follow the tutorial. Before you want `Yarn Build`, now use the` Create DataBase if Not Exists UMAMI in your database; create a UMAMI database, and then change the name of the library of the configuration file to UMAMI (the same as the database name you created) Essence Then ** Don't use the SQL statement it provided to create a table, because you will automatically create table ** after you start.

After that, execute build and execute Start (if the start is due to the port occupation, you can use the `yarn start -port = 3001` to modify the port). This service is started even if it starts. For how to configure nginx, log in, modify passwords, etc., you can refer to this blog[Use UMAMI self -built website traffic statistics analysis tool -ATPX](https://atpx.com/blog/build-umami-web-analytics)Essence

At this point, UMAMI should be able to use it normally. If the console prompts the wrong `Failed to load resource: net :: err_blockd_by_client`, it should be blocked by advertising interceptors such as Adblock. You can turn off your advertising interceptor and get rid of it Come to solve it, but there is no good way to avoid the interceptor of the advertising interceptor, so the data may not be so accurate.

## Summarize

After reading the above content, I believe that you are familiar with the basic process of building your own blog; ** understanding is very important, and practice is just as important. In the process of building a personal blog, due to the different environment, the theme of the selection, and personal experience, the problems encountered must be different. The most important thing in this process is ** patience **, willing to spend time to try to solve the problems encountered, grow up in learning, and learn in growth. Just like the cover of this article, Monet's water lily symbolizes tranquility and patience. I also wish all students who want to build their own blogs, and students who want to achieve their goals, although it is impossible for everything to be smooth, as long as they have enough patience and ability to discover and solve problems, solve problems, solve problems, and solve problems. Ask for help from the outside world if you can't help the outside world, ** will definitely get something and it will be achieved. **
