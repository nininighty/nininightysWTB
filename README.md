# 错题本项目

## 简介
这是一个基于 Flask 的错题本管理系统，支持用户登录、错题管理、错题复习、自动生成错题卷等功能。

## AI声明
本人专业并非计算机，完成这个项目的原因是出于去年在跨考11408过程中对于错题的抄写繁复耗时。
本项目在实现全程在ChatGPT的指导下完成，同时由于我没学过css与js、html，大部分代码是我参考或直接使用GPT完成的代码。  
所有代码均已由本人整理、测试并最终确认。如有问题，欢迎提交 issue。


## 适合用户
请注意，不是所有的用户都适合使用一个网站作为错题本，所以请一定要阅读以下条件对您来说是否合适：
- *更适合电脑考研*：  
① 整体ui均以PC为出发点开发，兼顾了一定的平板ui。  
② PC端浏览器打开错题卷会打开新的页面而不是像移动端浏览器一样下载一份PDF。  
③ 错题详情界面的答案只能上传图片文件与解答链接，PC端点击和粘贴讲解视频链接更方便。
-  *考研11408*：  
我在git中同步了官方错题集，因为本人是11408所以已经备好了一些我用脚本裁剪的题目
- *PDF资源丰富*：  
网站没有拍摄功能，所以你如果需要上传自己的错题并要求生成的错题卷的打印效果良好请务必上传清晰的pdf

## 服务器所需第三方软件
- MySQL：/SetUp中已经准备好了建库脚本
- 

## 目录结构
- `/static` —css源码，以及网站图片字体资源
- `/templates` — html源码文件夹
- `/SetUp` — 部署相关文件，如数据库建表脚本、nginx 配置等
- `/WTBs` — 错题本资源存储文件夹，包括官方错题集、用户上传的图片头像等资源以及默认头像文件
- `.env.example` — 环境变量模板，请参考配置示范完成您的环境
- `requirements.txt` — Python 依赖包列表
- `Timer_aggerate_scores.py` — 每日清点错题卷完成记录，更新题目完成情况的脚本
- `Timer_generate_daily_papers.py` — 生成每日错题卷的脚本
- `db_utils.py` —自定义数据库模块，以及错题卷题目拣选逻辑
- 其余各文件用途请参看文件首部，因为这是我的首个项目所以文件排布混乱敬请谅解 :(


## 环境准备
1. 创建并激活虚拟环境  
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows

查看 nginx 主配置文件位置  
```bash
nginx -V 2>&1 | grep -- '--conf-path'
```


## 定时任务脚本配置（统计用户得分和生成错题卷）
### Linux
   打开 crontab 编辑器
   ```bash
   crontab -e
   ```
   添加任务，注意对应的时刻和分钟对应env配置中的设置，同时修改对应的路径为您服务器上的文件绝对路径  
1、定时统计每日得分情况，我设定的是23:59
```bash
59 23 * * * /bin/bash /home/your_user/wtb/SetUp/run_aggregate.sh >> /home/your_user/wtb/logs/aggregate.log 2>&1
```
2、定时生成每日错题卷，我设定的是00:00
```bash
 0 0 * * * /bin/bash /home/your_user/wtb/SetUp/run_generate_papers.sh >> /home/your_user/wtb/logs/generate_papers.log 2>&1
   ```

## 可能的问题
ECSpython版本过低导致requirements安装失败