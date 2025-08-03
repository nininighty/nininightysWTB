#!/bin/bash
# 启动Nginx

# 读取根目录的 .env 文件中的 VENV_PATH
VENV_PATH=$(grep -v '^#' ../.env | grep VENV_PATH | cut -d '=' -f2)

if [ -z "$VENV_PATH" ]; then
  echo "Error: VENV_PATH not set in ../.env"
  exit 1
fi

# 激活虚拟环境
source "$VENV_PATH/bin/activate"

# 启动 Gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
