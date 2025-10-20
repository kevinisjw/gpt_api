## 八字计算api
- 计算八字
```json
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
```json
curl "http://localhost:8100/bazi/health"
```
- info 
```json
curl "http://localhost:8100/bazi/info"
```


## 命运测算api
- 文本生成
```bash
curl -X POST "http://localhost:8000/generate" \
-H "Content-Type: application/json" \
-d '{
  "prompt": "请帮我测算命运，我的八字信息如下：xxx",
  "output_type": "text",
  "stream": false
}'
```

- 流式文本生成
```bash
curl -X POST "http://localhost:8000/generate/stream" \
-H "Content-Type: application/json" \
-d '{
  "prompt": "解释机器学习",
  "output_type": "text",
  "stream": true
}'
```