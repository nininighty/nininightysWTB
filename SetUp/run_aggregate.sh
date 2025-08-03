#!/bin/bash
# 每日定时统计得分情况脚本

get_env_var() {
  grep -v '^#' ../.env | grep "^$1=" | head -n1 | cut -d '=' -f2- | tr -d '"'
}

VENV_PATH=$(get_env_var "VENV_PATH")
if [ -z "$VENV_PATH" ]; then
  echo "VENV_PATH 未设置"
  exit 1
fi

source "$VENV_PATH/bin/activate"

python ../Timer_aggerate_scores.py
