# CentOS 7 + RTX 4090（CUDA 11.8）Docker 部署文档

本文档用于在 **CentOS 7** 服务器上，以 **Docker + NVIDIA Container Toolkit** 方式部署本项目 `invoicerecognition`，并启用 **RTX 4090** 进行 GPU 推理（含 **PaddleOCR GPU**）。

---

## 1. 部署目标与端口约定

- **应用**：Flask/Gunicorn（容器内监听 `0.0.0.0:5000`）
- **数据库**：MySQL（建议容器化）
- **对外入口**：Nginx（宿主机 `80/443` → 反代到 `5000`）
- **SSE 进度条**：`/api/predict/stream`（Nginx 必须关闭 buffering）

---

## 2. 宿主机准备（CentOS 7）

### 2.1 禁用 nouveau（必须）

```bash
sudo bash -c 'cat >/etc/modprobe.d/blacklist-nouveau.conf <<EOF
blacklist nouveau
options nouveau modeset=0
EOF'
sudo dracut --force
sudo reboot
```

### 2.2 安装 NVIDIA Driver（必须）

RTX 4090 建议 **535+** 驱动。安装方式可用 `.run` 或 ELRepo，装完后验证：

```bash
nvidia-smi
```

能正常看到 GPU 信息即 OK。

---

## 3. 安装 Docker 与 NVIDIA Container Toolkit（宿主机）

### 3.1 安装 Docker

```bash
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl enable --now docker
```

### 3.2 安装 NVIDIA Container Toolkit

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

sudo yum install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 3.3 验证容器可用 GPU

```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-runtime-ubuntu22.04 nvidia-smi
```

---

## 4. 部署目录与项目准备

建议将项目部署到：

```bash
sudo mkdir -p /opt/invoicerecognition
```

将代码同步到 `/opt/invoicerecognition`（scp/rsync/git 均可）。

确保包含：

- `app.py`
- `requirements.txt`
- `best.pt`（YOLO 权重）
- `.env`（从 `.env.example` 复制并填写）

### 4.1 创建 `.env`

在 `/opt/invoicerecognition/.env`（示例）： 

```env
DB_HOST=mysql
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=invoice_recognition

# 阿里云发票核验（可选）
ALIYUN_APPCODE=your_appcode_here

# 可选：供 Dify 工具函数使用
API_BASE_URL=http://localhost:5000
```

---

## 5. Dockerfile（CUDA 11.8 + PaddlePaddle GPU + PaddleOCR）

在 `/opt/invoicerecognition/Dockerfile` 写入：

```dockerfile
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN python3 -m pip install --upgrade pip

# 关键：先装 PaddlePaddle GPU（CUDA 11.8）
RUN python3 -m pip install -U \
    paddlepaddle-gpu==2.6.2 \
    -f https://www.paddlepaddle.org.cn/packages/stable/cu118/

# 再装项目依赖（含 paddleocr、ultralytics 等）
RUN python3 -m pip install -r /app/requirements.txt

RUN python3 -m pip install gunicorn

COPY . /app

EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-k", "gthread", "--threads", "4", "-b", "0.0.0.0:5000", "app:app"]
```

说明：

- `paddlepaddle-gpu` 必须安装，否则 PaddleOCR 很可能走 CPU。
- `libgl1/libglib2.0-0` 用于解决 OpenCV 常见的 `libGL.so` 相关报错。

---

## 6. docker-compose（MySQL + App + GPU）

在 `/opt/invoicerecognition/docker-compose.yml` 写入：

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: your_password
      MYSQL_DATABASE: invoice_recognition
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
    volumes:
      - ./_data/mysql:/var/lib/mysql
    ports:
      - "3306:3306"

  app:
    build: .
    env_file:
      - .env
    volumes:
      - ./uploads:/app/uploads
      - ./output:/app/output
      - ./best.pt:/app/best.pt
    ports:
      - "5000:5000"
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
```

> 如果你的 `docker compose` 版本不支持 `deploy.resources...` 的 GPU 预留方式，可改为旧写法（视环境而定）：  
> `runtime: nvidia` 或在启动时使用 `--gpus all`。

启动：

```bash
cd /opt/invoicerecognition
docker compose up -d --build
docker compose logs -f app
```

---

## 7. Nginx 反向代理（含 SSE）

### 7.1 安装 Nginx

```bash
sudo yum install -y nginx
sudo systemctl enable --now nginx
```

### 7.2 配置 `/etc/nginx/conf.d/invoicerecognition.conf`

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # SSE：关闭缓冲/缓存，延长超时，否则进度条会不更新
    location /api/predict/stream {
        proxy_pass http://127.0.0.1:5000/api/predict/stream;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600;
    }
}
```

重载：

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 8. 部署验证（强烈建议逐项检查）

### 8.1 服务健康检查

```bash
curl http://localhost:5000/api/health
```

### 8.2 容器内 GPU 可用性

```bash
docker exec -it $(docker ps -qf name=app) bash -lc "nvidia-smi"
```

### 8.3 Paddle 是否启用 CUDA（容器内）

```bash
docker exec -it $(docker ps -qf name=app) bash -lc \
"python3 -c \"import paddle; print('cuda:', paddle.is_compiled_with_cuda()); print('device:', paddle.device.get_device())\""
```

期望输出：

- `cuda: True`
- `device: gpu:0`

### 8.4 SSE 进度流验证（进度条不更新必查）

```bash
curl -N -X POST http://localhost:5000/api/predict/stream -F "files[]=@invoice_00001.jpg"
```

应持续输出 `data: {...}` 的 SSE 行。

---

## 9. 常见问题与排错

### 9.1 进度条不更新

- Nginx 必须配置：
  - `proxy_buffering off;`
  - `proxy_read_timeout` 足够大
- 前端需使用 `/api/predict/stream`（SSE）接口。

### 9.2 PaddleOCR 仍然跑 CPU

- 确认容器内已安装 `paddlepaddle-gpu`：

```bash
docker exec -it $(docker ps -qf name=app) bash -lc "python3 -c \"import paddle; print(paddle.__version__); print(paddle.is_compiled_with_cuda())\""
```

- 若为 False：检查 Dockerfile 中 `paddlepaddle-gpu` 安装命令是否执行成功。

### 9.3 OpenCV 报 `libGL.so` 等依赖错误

确保 Dockerfile 已安装：
- `libgl1`
- `libglib2.0-0`

---

## 10. 维护命令速查

```bash
# 查看容器
docker compose ps

# 查看应用日志
docker compose logs -f app

# 重启应用
docker compose restart app

# 重新构建并启动
docker compose up -d --build
```

