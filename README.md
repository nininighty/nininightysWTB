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
- Nginx

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


## 环境要求

- MySQL 8.0.x  
  - 需要安装并启动 MySQL 服务  
  - 用 root 登录 MySQL，创建数据库和专用用户：
    ```sql
    CREATE DATABASE WTB_SQL DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER '数据库用户名'@'localhost' IDENTIFIED BY '数据库用户的密码';
    GRANT ALL PRIVILEGES ON WTB_SQL.* TO 'wtb_user'@'localhost';
    FLUSH PRIVILEGES;
    EXIT;
    ```
    使用新建的用户（以wtb_user为例）用户导入初始化脚本：
     ```bash
    mysql -u wtb_user -p WTB_SQL < SetUp/user_system_schema.sql
    ```

- Python 3.9+  
  - 推荐使用虚拟环境  
  - 安装依赖：`pip install -r requirements.txt`

- Gunicorn
  ```bash
  pip install gunicorn
  ```
- libpango -1.0-9
  - 请在配置虚拟环境完成后安装libpango，该插件负责渲染错题卷的pdf文件，安装代码如下：
  ```bash
     sudo yum install -y pango pango-devel cairo cairo-devel gdk-pixbuf2 gdk-pixbuf2-devel libffi-devel
     ```
  - Windows环境下可以访问以下网址安装GTK环境：
  ```
  https://github.com/tschoonj/gtk-for-windows-runtime-environment-installer/releases?utm_source=chatgpt.com
  ```

## Windows ECS部署步骤
①安装环境：python、Nginx、MySQL以及GTK  
②在目标文件夹下创建虚拟环境并安装需要的包  
③配置Nginx的conf文件  
④创建一份bat文件用于切换到对应虚拟环境并运行`run_waitress.py`，之后启动服务器只需要执行bat文件即可

## Linux ECS部署步骤
作者在Linux上部署遇到了诸多问题，作为一个代码新手来说我不推荐linux，同时以下的部署步骤可能会出现问题，很抱歉本项目暂时无法提供解答
### ①激活虚拟环境
```bash
cd ~/你的项目目录
source venv311/bin/activate
```

### ②后台启动Gunicorn并测试本机服务
```bash
gunicorn -w 4 -b 127.0.0.1:8000 SetUp.wsgi:app --daemon
curl http://127.0.0.1:8000/
```
测试完成后关闭Gunicorn进程
```bash
ps aux | grep gunicorn
pkill -f gunicorn
```
### ③修改本地配置文件  
请先在您的服务器上建立一个备份的文件夹，然后返回项目目录填写配置  
创建.env环境配置的文件
```bash
cp .env.example .env
```
查询Nginx的目录可用
```bash
ls -ld /etc/nginx/conf.d
```

### ④进入SetUp文件夹，执行部署脚本
完成Nginx的部署，成功时显示：  
"【成功】nginx 配置生成并已重启，代理目标：..."
```bash
bash gen_nginx_conf.sh
```
完成systemd的部署
```bash
bash gen_systemd.sh
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
### Windows
打开“任务计划程序”，运行bat脚本。bat脚本的内容为执行对应的py文件，记得切换到对应的虚拟环境

## 可能的问题
ECS上python版本过低导致requirements安装失败，建议至少python3.9以上
