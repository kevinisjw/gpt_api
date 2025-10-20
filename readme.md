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
