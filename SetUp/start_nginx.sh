#!/bin/bash

# 检查是否有 root 权限
if [ "$EUID" -ne 0 ]; then
  echo "请使用 root 权限运行此脚本（sudo）"
  exit 1
fi

# 启动 nginx 服务
sudo systemctl start nginx

# 检查 nginx 状态
if systemctl is-active --quiet nginx; then
  echo "✅ nginx 已启动"
else
  echo "❌ nginx 启动失败"
  exit 1
fi
