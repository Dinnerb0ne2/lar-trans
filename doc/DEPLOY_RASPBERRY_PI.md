# 树莓派部署指南

## 1. 网络拓扑

1. 服务器开启热点（或同一局域网）。
2. 树莓派连接该热点。
3. 客户端 `--server-url` 指向服务端 IP。

## 2. 树莓派端准备

```bash
python3 --version
# 确保 3.11.x

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. USB 摄像头检查

```bash
ls /dev/video*
```

默认摄像头索引为 `0`，如果多个摄像头可改 `--camera-index`。

## 4. 服务端启动

```bash
python -m server.main --host 0.0.0.0 --port 8000
```

## 5. 客户端启动

```bash
python -m client.main \
  --server-url http://<server-ip>:8000 \
  --client-id pi-cam-01 \
  --camera-index 0 \
  --fps 10 \
  --resolution 480p \
  --silent
```

## 6. systemd 自启动（可选）

创建 `/etc/systemd/system/lar-trans-client.service`:

```ini
[Unit]
Description=lar-trans client
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/pi/lar-trans
ExecStart=/home/pi/lar-trans/.venv/bin/python -m client.main --server-url http://<server-ip>:8000 --client-id pi-cam-01 --camera-index 0 --silent
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用:

```bash
sudo systemctl daemon-reload
sudo systemctl enable lar-trans-client
sudo systemctl start lar-trans-client
sudo systemctl status lar-trans-client
```

## 7. 远程调度节能

在服务端通过 `PATCH /api/v1/client/{client_id}/config` 设置 `schedule_windows`，可配置多段时段。客户端会自动按生效配置启停采集，无需重启。
