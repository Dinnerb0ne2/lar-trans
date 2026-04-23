# API 文档

## 基础信息

- Base URL: `http://<server-ip>:8000`
- 数据格式: JSON / Multipart

## 1. 健康检查

`GET /health`

响应:

```json
{"status":"ok"}
```

## 2. 获取所有客户端状态

`GET /api/v1/clients`

响应:

```json
{
  "items": [
    {
      "client_id": "pi-cam-01",
      "desired_config": {},
      "effective_config": {},
      "last_heartbeat": "2026-04-23T21:00:00",
      "last_stats": {}
    }
  ]
}
```

## 3. 获取单客户端配置

`GET /api/v1/client/{client_id}/config`

响应字段:

- `desired_config`: 服务端存储的目标配置（fps/resolution/silent/schedule/manual）
- `effective_config`: 服务端当前生效配置（是否允许采集）
- `server_time`: 服务端时间

## 4. 更新客户端配置

`PATCH /api/v1/client/{client_id}/config`

请求体示例:

```json
{
  "fps": 8,
  "resolution": "360p",
  "silent": true,
  "schedule_windows": [
    {"start":"08:00","end":"10:00"},
    {"start":"18:30","end":"22:30"}
  ],
  "manual_enabled": null
}
```

约束:

- `fps`: 3~15
- `resolution`: `360p` 或 `480p`
- 时间格式: `HH:MM`

## 5. 手动控制客户端采集

1. `POST /api/v1/client/{client_id}/control/start`  
   强制开启采集（覆盖计划）
2. `POST /api/v1/client/{client_id}/control/stop`  
   强制停止采集（覆盖计划）
3. `POST /api/v1/client/{client_id}/control/auto`  
   恢复计划/自动模式

## 6. 客户端心跳

`POST /api/v1/heartbeat`

请求体:

```json
{
  "client_id":"pi-cam-01",
  "stats":{
    "frames_sent": 120,
    "last_result_count": 2
  }
}
```

响应:

服务端会返回同 `GET /api/v1/client/{client_id}/config` 格式，客户端可直接应用。

## 7. 上传帧并触发 LightArmyRecon

`POST /api/v1/client/{client_id}/frame`

请求:

- `multipart/form-data`
- 字段名：`frame`
- 内容：PNG 图像数据

响应示例:

```json
{
  "result_count": 1,
  "results": [
    {
      "bbox":[10,20,100,120],
      "name":"Unknown",
      "similarity":0.0
    }
  ]
}
```
