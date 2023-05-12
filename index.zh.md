---
title: "Windows配置免密登录Ubuntu不生效的问题"
date: 2023-04-15T00:05:26+08:00
description: ""
toc: true
categories: ["技术"]
image: cover.jpg
tags: ["运维", "SSH", "Ubuntu"]
keywords: ["运维", "SSH", "Ubuntu"]
---

# Windows配置免密登录Ubuntu不生效的问题

## 起因

在配置我的个人博客期间，打算使用Github Action进行自动部署，其中需要使用SSH密钥的方式来进行免密登录。

## 参考链接

1. [如何在Ubuntu 20.04配置SSH密钥免密码登录](https://www.myfreax.com/how-to-set-up-ssh-keys-on-ubuntu-20-04/)

2. [解决SSH免密登录配置成功后不生效问题](https://blog.csdn.net/lisongjia123/article/details/78513244)

## 配置

博主使用的是win10，Ubuntu20.04；

配置密钥的流程很简单，首先使用生成密钥对

```shell
ssh-keygen -t rsa -q -C "For SSH" -f rsa_id
```

然后使用`ssh-copy-id remote_username@server_ip_address` 将公钥部署到远程服务器上，但是Windows一般没有`ssh-copy-id`命令，所以可以使用下面命令替代。

```shell
cat ~/.ssh/id_rsa.pub | ssh remote_username@server_ip_address "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

之后，重启ssh服务，使用`ssh remote_username@server_ip_address` 连接发现仍然需要密码，查阅资料过后，链接2是在Linux平台上的，不适用Windows。百思不得其解。

## 解决方法

发现服务中的OpenSSH Authentication Agent这一项没有启动，其描述已经很清楚，就是用来做公私钥验证的，把服务开启后，再次尝试仍然无法直接连接。

<img src="image-20230413143814145.png" alt="image-20230413152155447" style="zoom:50%;" />

最后，在你的.ssh目录下添加config文件

```yaml
Host yourhost
     Hostname yourhost
     Port 22
     User youruser
     IdentityFile ~/.ssh/your_key
```

保存后重新连接，完美解决！
<img src="image-20230413144414536.png" alt="image-20230413152155447" style="zoom:80%;" />

