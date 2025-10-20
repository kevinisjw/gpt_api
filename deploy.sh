#!/usr/bin/env bash
# 一键构建并启动 OpenRouter API + Web 前端

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
ENV_FILE="$PROJECT_DIR/.env"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "未找到 $COMPOSE_FILE，请确认脚本位于项目根目录。" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "未找到 $ENV_FILE，请先创建环境变量文件（可复制 .env.example 再修改）。" >&2
  exit 1
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "未找到 docker compose 或 docker-compose，请先安装 Docker。" >&2
  exit 1
fi

echo "使用 ${COMPOSE_CMD[*]} 构建并启动服务..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up -d --build

echo "服务已启动，可访问 http://127.0.0.1:8000/face 或 /fortune"
