#!/bin/bash

echo "当前路径：$(pwd)"
echo "VENV_PATH=$VENV_PATH"

# 读取根目录的 .env 文件中的 VENV_PATH
VENV_PATH=$(grep -v '^#' "$PWD/.env" | grep VENV_PATH | cut -d '=' -f2)

if [ -z "$VENV_PATH" ]; then
  echo "Error: VENV_PATH not set in ../.env"
  exit 1
fi

echo "激活虚拟环境：$VENV_PATH/bin/activate"
source "$VENV_PATH/bin/activate"

echo "虚拟环境激活完成，python版本：$(python --version)"

# 确保日志目录存在
mkdir -p logs

echo "启动 Gunicorn"
gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log

echo "脚本结束"
