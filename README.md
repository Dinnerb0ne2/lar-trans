# lar-trans (Python 3.11.0)

树莓派内网监控传输系统：  
- **client** 采集 USB 摄像头图像（PNG 无损）并上传到 server。  
- **server** 接收图像并调用 `../LightArmyRecon` 做识别处理（不改动其原有功能）。  
- 支持远程动态调参、心跳、自动重连、定时启停、多时段节能运行。

## 1. 功能清单

1. PNG 无损传输（`image/png`，OpenCV PNG 编码）。
2. 分辨率：`360p` / `480p`。
3. 帧率：`3~15 FPS`。
4. 静默模式：后台运行，不弹窗，但保留 CLI 日志输出。
5. 服务端远程调整 client 参数（分辨率、FPS、静默、时段、手动启停）。
6. client 定时心跳（默认每 10 秒）维持连接状态。
7. client 自动重连（网络失败指数退避）。
8. server 支持多时段计划调度（跨天时段也支持）。

## 2. 项目结构

```text
lar-trans/
├── client/
│   ├── camera.py
│   ├── controller.py
│   ├── logging_utils.py
│   ├── main.py
│   └── server_api.py
├── common/
│   └── protocol.py
├── server/
│   ├── app.py
│   ├── main.py
│   ├── recon_adapter.py
│   ├── schedule.py
│   ├── schemas.py
│   └── state.py
├── tests/
│   ├── test_schedule.py
│   └── test_server_api.py
├── doc/
│   ├── API.md
│   └── DEPLOY_RASPBERRY_PI.md
└── requirements.txt
```

## 3. 环境准备（Python 3.11.0）

```powershell
python --version
# 需显示 Python 3.11.0

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 4. 启动服务端

```powershell
python -m server.main --host 0.0.0.0 --port 8000 --state-file server\state.json
```

> 服务端默认会从 `..\LightArmyRecon` 加载模型与数据库并处理上传帧。

## 5. 启动客户端（树莓派）

```powershell
python -m client.main ^
  --server-url http://<server-ip>:8000 ^
  --client-id pi-cam-01 ^
  --camera-index 0 ^
  --fps 10 ^
  --resolution 480p ^
  --silent
```

## 6. 服务端远程控制示例

### 调整参数

```powershell
curl -X PATCH "http://127.0.0.1:8000/api/v1/client/pi-cam-01/config" ^
  -H "Content-Type: application/json" ^
  -d "{\"fps\":8,\"resolution\":\"360p\",\"silent\":true}"
```

### 设置多时段启动

```powershell
curl -X PATCH "http://127.0.0.1:8000/api/v1/client/pi-cam-01/config" ^
  -H "Content-Type: application/json" ^
  -d "{\"schedule_windows\":[{\"start\":\"08:00\",\"end\":\"10:00\"},{\"start\":\"18:30\",\"end\":\"22:30\"}]}"
```

### 手动启停（覆盖计划）

```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/client/pi-cam-01/control/start"
curl -X POST "http://127.0.0.1:8000/api/v1/client/pi-cam-01/control/stop"
curl -X POST "http://127.0.0.1:8000/api/v1/client/pi-cam-01/control/auto"
```

## 7. 测试

```powershell
pytest -q
```

## 8. 版本控制（git）

```powershell
git status
git add .
git commit -m "feat: implement raspberry-pi monitor client/server pipeline"
```

详细接口和部署说明见 `doc/API.md` 与 `doc/DEPLOY_RASPBERRY_PI.md`。
