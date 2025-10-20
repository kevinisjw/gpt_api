#!/usr/bin/env bash
# 启动 gpt_services.py 后端服务，并在准备就绪后打开 face_teller.html 页面。

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
SERVICE_PORT=8000
SERVICE_APP="$PROJECT_DIR/gpt_api/gpt_services.py"
FRONTEND_URL="http://127.0.0.1:${SERVICE_PORT}/face"

mkdir -p "$LOG_DIR"

free_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti TCP:"$port" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "检测到端口 $port 被占用，尝试结束相关进程..."
    for pid in $pids; do
      if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" >/dev/null 2>&1 || true
      fi
    done
    sleep 1
  fi
}

wait_for_port() {
  local port="$1"
  local retries=40
  local delay=0.5

  for ((i = 0; i < retries; i++)); do
    if python3 - <<PY >/dev/null 2>&1
import socket
with socket.socket() as sock:
    sock.settimeout(0.5)
    sock.connect(("127.0.0.1", $port))
PY
    then
      return 0
    fi
    sleep "$delay"
  done

  echo "等待端口 $port 启动超时，请检查服务日志：logs/gpt_service.log" >&2
  return 1
}

start_service() {
  echo "启动 GPT 面相服务 (gpt_services.py)..."
  nohup python3 "$SERVICE_APP" 2>&1 &
  SERVICE_PID=$!
  if [[ -z "${SERVICE_PID}" ]]; then
    echo "GPT 服务启动失败，请检查：$SERVICE_APP" >&2
    exit 1
  fi
  echo "GPT 服务 PID: ${SERVICE_PID}，日志: logs/gpt_service.log"
}

cleanup() {
  echo
  echo "正在停止 GPT 服务..."
  if [[ -n "${SERVICE_PID:-}" ]] && kill -0 "${SERVICE_PID}" 2>/dev/null; then
    kill "${SERVICE_PID}" >/dev/null 2>&1 || true
    wait "${SERVICE_PID}" >/dev/null 2>&1 || true
  fi
  echo "服务已停止。"
}

trap cleanup EXIT INT TERM

free_port "$SERVICE_PORT"
start_service

echo "等待 GPT 服务启动..."
wait_for_port "$SERVICE_PORT"

echo "服务就绪，尝试打开页面：$FRONTEND_URL"
if command -v open >/dev/null 2>&1; then
  open "$FRONTEND_URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$FRONTEND_URL"
else
  echo "无法自动打开浏览器，请手动访问：$FRONTEND_URL"
fi

echo "按 Ctrl+C 可停止服务。"
wait
