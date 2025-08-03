#!/bin/bash
# 每日生成系统错题卷脚本

get_env_var() {
  grep -v '^#' ../.env | grep "^$1=" | head -n1 | cut -d '=' -f2- | tr -d '"'
}

VENV_PATH=$(get_env_var "VENV_PATH")
if [ -z "$VENV_PATH" ]; then
  echo "VENV_PATH 未设置"
  exit 1
fi

source "$VENV_PATH/bin/activate"

python ../Timer_generate_daily_papers.py
