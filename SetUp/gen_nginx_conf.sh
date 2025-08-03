#!/bin/bash
# 根据 ../.env 自动生成 nginx 配置并重启 nginx，所有敏感信息均从 .env 读取

# 读取变量函数
get_env_var() {
    grep -v '^#' ../.env | grep "^$1=" | head -n1 | cut -d '=' -f2- | tr -d '"'
}

IP_PATH=$(get_env_var "IP_PATH")
SERVER_NAME=$(get_env_var "SERVER_NAME")
NGINX_CONF_DIR=$(get_env_var "NGINX_CONF_DIR")

# 校验变量是否存在
if [ -z "$IP_PATH" ]; then
  echo "错误：.env 配置文件中没有填写 IP_PATH 字段！"
  exit 1
fi

if [ -z "$SERVER_NAME" ]; then
  echo "错误：.env 配置文件中没有填写 SERVER_NAME 字段！"
  exit 1
fi

if [ -z "$NGINX_CONF_DIR" ]; then
  echo "错误：.env 配置文件中没有填写 NGINX_CONF_DIR 字段！"
  exit 1
fi

# 校验 IP_PATH 是否包含端口
if [[ ! "$IP_PATH" =~ :[0-9]+$ ]]; then
  echo "警告：IP_PATH 中缺少端口号，请在 .env 中的 IP_PATH 加上 :5000 端口。"
fi

# 提取 IP和端口部分
IP_PORT=$(echo "$IP_PATH" | sed -E 's|^http://([^/]+)/?.*|\1|')
IMG_PREFIX="/img"

# 生成 nginx 配置文件
cat > /tmp/wtb.conf <<EOF
server {
    listen 80;
    server_name $SERVER_NAME;

    location $IMG_PREFIX/ {
        proxy_pass http://$IP_PORT$IMG_PREFIX/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        proxy_pass http://$IP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root html;
    }
}
EOF

# 拷贝到 nginx 配置目录
sudo cp /tmp/wtb.conf "$NGINX_CONF_DIR/wtb.conf"

# 测试配置并重启 nginx
if sudo nginx -t; then
    sudo systemctl restart nginx
    echo "【成功】nginx 配置生成并已重启，代理目标：$IP_PATH，域名：$SERVER_NAME"
else
    echo "【失败】nginx 配置测试失败，请检查配置文件。"
fi
