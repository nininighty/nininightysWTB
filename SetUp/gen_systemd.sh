#!/bin/bash
# 配置systemd服务

# 读取变量函数
get_env_var() {
  grep -v '^#' ../.env | grep "^$1=" | head -n1 | cut -d '=' -f2- | tr -d '"'
}

PROJECT_PATH=$(get_env_var "LOCAL_PATH")
USER_NAME=$(get_env_var "SERVICE_USER")
SERVICE_NAME=$(get_env_var "SERVICE_NAME")

# 检查必要变量是否存在
if [ -z "$PROJECT_PATH" ] || [ -z "$USER_NAME" ] || [ -z "$SERVICE_NAME" ]; then
  echo "错误：请确保 .env 文件中包含 LOCAL_PATH, SERVICE_USER 和 SERVICE_NAME 三个变量"
  exit 1
fi

SERVICE_FILE_CONTENT="[Unit]
Description=$SERVICE_NAME Service
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$PROJECT_PATH

ExecStart=/bin/bash $PROJECT_PATH/SetUp/start.sh

Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
"

echo "$SERVICE_FILE_CONTENT" > /tmp/${SERVICE_NAME}.service

sudo mv /tmp/${SERVICE_NAME}.service /etc/systemd/system/${SERVICE_NAME}.service
sudo systemctl daemon-reload

echo "$SERVICE_NAME systemd 服务已生成并重载"
