#!/bin/bash
#数据库备份脚本

get_env_var() {
  grep -v '^#' ../.env | grep "^$1=" | head -n1 | cut -d '=' -f2- | tr -d '"'
}

BACKUP_DIR=$(get_env_var "BACKUP_DIR")
MYSQL_USER=$(get_env_var "MYSQL_USER")
MYSQL_PASS=$(get_env_var "MYSQL_PASS")
MYSQL_NAME=$(get_env_var "MYSQL_NAME")

if [ -z "$BACKUP_DIR" ] || [ -z "$MYSQL_USER" ] || [ -z "$MYSQL_PASS" ] || [ -z "$MYSQL_NAME" ]; then
  echo "请确保 .env 文件中包含 BACKUP_DIR, MYSQL_USER, MYSQL_PASS, MYSQL_NAME"
  exit 1
fi

mkdir -p "$BACKUP_DIR"

mysqldump -u "$MYSQL_USER" -p"$MYSQL_PASS" "$MYSQL_NAME" > "$BACKUP_DIR/mysql_backup_$(date +%F).sql"

