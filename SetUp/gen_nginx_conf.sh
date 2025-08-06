#!/bin/bash
# 根据 ../.env 自动生成 nginx 配置并重启 nginx

get_env_var() {
    grep -v '^#' ../.env | grep "^$1=" | head -n1 | cut -d '=' -f2- | tr -d '"'
}

SERVER_NAME=$(get_env_var "SERVER_NAME")
NGINX_CONF_DIR=$(get_env_var "NGINX_CONF_DIR")


if [ -z "$SERVER_NAME" ]; then
  echo "错误：.env 中没有 SERVER_NAME！"
  exit 1
fi

if [ -z "$NGINX_CONF_DIR" ]; then
  echo "错误：.env 中没有 NGINX_CONF_DIR！"
  exit 1
fi


IMG_PREFIX="/img"

cat > /tmp/wtb.conf <<EOF
server {
    listen 80;
    server_name $SERVER_NAME;

    location $IMG_PREFIX/ {
        proxy_pass http://127.0.0.1:5000$IMG_PREFIX/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
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

sudo cp /tmp/wtb.conf "$NGINX_CONF_DIR/wtb.conf"

if sudo nginx -t; then
    sudo systemctl restart nginx
    echo "【成功】nginx 配置生成并重启，代理目标为127.0.0.1:5000，域名：$SERVER_NAME"
else
    echo "【失败】nginx 配置测试失败"
fi
