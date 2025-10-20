## 八字计算api
- 计算八字
```bash
curl -X POST "http://localhost:8100/bazi/compute" \
    -H "Content-Type: application/json" \
    -d '{
      "birth_datetime": "1982-10-28 12:00:00",
      "location_name": "中国南宁市",
      "gender": "女",
      "name": "王鸥"
    }'
```
- 健康检查
```bash
curl "http://localhost:8100/bazi/health"
```
- info 
```bash
curl "http://localhost:8100/bazi/info"
```

## 一键部署网页 + API

1. 准备 `.env`：可以参考 `.env.example`，至少需要设置 `OPENROUTER_API_KEY`。
2. 安装并启动 Docker 服务（支持 `docker compose` 或 `docker-compose`）。
3. 在项目根目录执行：

   ```bash
   ./deploy.sh
   ```

   脚本会自动构建镜像并启动容器，默认监听 `8000` 端口。

部署完成后：
- 访问 `http://服务器IP:8000/face` 获取面相分析页面。
- 访问 `http://服务器IP:8000/fortune` 获取命运测算页面。
- API 入口保持为 `http://服务器IP:8000/generate`。

停止服务：

```bash
docker compose -f docker-compose.yml down
# 或者使用 docker-compose down
```

## 命运测算 API（统一 `/generate` 入口）

### 五行命理（文本式八字解读）
一次性返回示例：
```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "is_stream": false,
    "user_call_data": {
      "task_info": {
        "user_id": "web-demo",
        "call_id": "demo-call-001",
        "call_time": "2025-01-01 12:00:00",
        "call_ip": "127.0.0.1",
        "task_id": "五行命理"
      },
      "user_input_info": {
        "text_info": {
          "birth_datetime": "1982-10-28 12:00:00",
          "location_name": "中国南宁市",
          "gender": "女",
          "name": "王鸥"
        },
        "image_info": {}
      }
    }
  }'
```

流式返回示例（使用 `curl -N` 持续输出）：
```bash
curl -N -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "is_stream": true,
    "user_call_data": {
      "task_info": {
        "user_id": "web-demo",
        "call_id": "demo-call-002",
        "call_time": "2025-01-01 12:05:00",
        "call_ip": "127.0.0.1",
        "task_id": "五行命理"
      },
      "user_input_info": {
        "text_info": {
          "birth_datetime": "1982-10-28 12:00:00",
          "location_name": "中国南宁市",
          "gender": "女",
          "name": "王鸥"
        },
        "image_info": {}
      }
    }
  }'
```

### 面相分析（图像 + 八字合参）
> `image_url` 需要传入 Base64 编码的图像数据（示例中用占位符表示）。

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "is_stream": true,
    "user_call_data": {
      "task_info": {
        "user_id": "web-demo",
        "call_id": "demo-call-003",
        "call_time": "2025-01-01 12:10:00",
        "call_ip": "127.0.0.1",
        "task_id": "面相分析"
      },
      "user_input_info": {
        "text_info": {
          "birth_datetime": "1982-10-28 12:00:00",
          "location_name": "中国南宁市",
          "gender": "女",
          "name": "王鸥"
        },
        "image_info": {
          "image_url": [
            "BASE64_ENCODED_JPEG_STRING"
          ],
          "image_type": "base64"
        }
      }
    }
  }'
```
