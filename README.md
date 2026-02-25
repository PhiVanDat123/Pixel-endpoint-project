# Pixel Endpoint Server

HTTP server nhận request mô tả pixel của ảnh, chạy trên 2 EC2 instance với Nginx làm Load Balancer.

## Kiến trúc

```
Client
  ↓
c5.xlarge:8000 (Nginx - Load Balancer)
  ↓                         ↓
c5.xlarge:8001           t2.xlarge:8000
(gunicorn × 9 workers)   (gunicorn × 9 workers)
```

## Thông tin máy chủ

| Instance | Type   | Vai trò              | Host                                        |
|----------|--------|----------------------|---------------------------------------------|
| c5       | c5.xlarge | Load Balancer + App | ec2-3-235-128-192.compute-1.amazonaws.com   |
| t2       | t2.xlarge | App                 | ec2-54-160-220-199.compute-1.amazonaws.com  |

**Public endpoint duy nhất:**
```
http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixel
```

---

## Cấu trúc project

```
pixel-server/
├── main.py              # FastAPI app
├── requirements.txt     # Python dependencies
├── gunicorn_config.py   # Gunicorn production config
├── nginx.conf           # Nginx full config (thay thế /etc/nginx/nginx.conf)
├── test.sh              # Script test throughput
└── README.md
```

---

## API Endpoints

### POST /pixel
Nhận request mô tả 1 pixel, lưu vào Redis.

**Request body:**
```json
{
  "x": 10,
  "y": 20,
  "channel": "R",
  "value": 128
}
```

| Field   | Type   | Mô tả                 |
|---------|--------|-----------------------|
| x       | int    | Toạ độ x              |
| y       | int    | Toạ độ y              |
| channel | string | R, G, hoặc B          |
| value   | int    | Giá trị pixel (0–255) |

**Response:**
```json
{"status": "ok"}
```

**curl:**
```bash
curl -X POST http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixel \
  -H "Content-Type: application/json" \
  -d '{"x":10,"y":20,"channel":"R","value":128}'
```

---

### GET /pixels
Trả về toàn bộ pixel đã nhận từ Redis (shared across tất cả workers).

**Response:**
```json
{
  "total": 3,
  "data": [
    {"x": 1, "y": 2, "channel": "R", "value": 128},
    {"x": 3, "y": 4, "channel": "G", "value": 200},
    {"x": 5, "y": 6, "channel": "B", "value": 55}
  ]
}
```

**curl:**
```bash
curl http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixels
```

---

### DELETE /pixels
Xóa toàn bộ pixel đã lưu trong Redis.

**Response:**
```json
{"status": "cleared"}
```

**curl:**
```bash
curl -X DELETE http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixels
```

---

### GET /health
Health check — trả lời thẳng từ Nginx, không qua app.

**Response:**
```json
{"status": "healthy", "pid": 1234, "store_size": 100}
```

**curl:**
```bash
curl http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/health
```

---

## Hướng dẫn Deploy

### Yêu cầu
- Ubuntu 22.04+
- Python 3.10+
- 2 EC2 instances (c5.xlarge và t2.xlarge)
- Port 8000 mở trên Security Group của c5

### 1. Clone repo và cài dependencies (cả 2 máy)

```bash
git clone <repo_url>
cd pixel-server

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Cài và chạy Redis trên c5 (chỉ c5)

Redis chạy trên c5, cả 2 app server đều ghi vào đây.

```bash
sudo apt install redis-server -y

# Cho phép kết nối từ t2 (thêm private IP của c5 vào bind)
sudo nano /etc/redis/redis.conf
# Sửa dòng: bind 127.0.0.1 → bind 127.0.0.1 <private-IP-c5>

sudo systemctl restart redis
sudo systemctl enable redis

# Kiểm tra
redis-cli ping   # → PONG
```

### 3. Chạy app trên t2 (port 8000)

```bash
source venv/bin/activate
# Trỏ REDIS_URL về private IP của c5
REDIS_URL=redis://172.31.6.171:6379 gunicorn main:app -c gunicorn_config.py --bind 172.31.25.176:8000
```

### 4. Chạy app trên c5 (port 8001)

```bash
source venv/bin/activate
REDIS_URL=redis://127.0.0.1:6379 gunicorn main:app -c gunicorn_config.py --bind 0.0.0.0:8001
```

### 5. Cấu hình Nginx trên c5

```bash
sudo apt install nginx -y

# Thay toàn bộ nginx.conf (không dùng sites-available)
sudo cp nginx.conf /etc/nginx/nginx.conf

# Sửa private IP của t2 nếu khác 172.31.25.176
sudo nano /etc/nginx/nginx.conf

# Kiểm tra và restart
sudo nginx -t
sudo systemctl restart nginx
```

> **Lưu ý:** File `nginx.conf` này thay thế `/etc/nginx/nginx.conf` hoàn toàn, không dùng `sites-available/sites-enabled` nữa.

---

## Hướng dẫn Test Throughput

### Cài vegeta

```bash
wget https://github.com/tsenart/vegeta/releases/download/v12.11.1/vegeta_12.11.1_linux_amd64.tar.gz
tar -zxvf vegeta_12.11.1_linux_amd64.tar.gz
```

### Chạy script test tự động (100 → 5000 req/s)

```bash
chmod +x test.sh
./test.sh
```

### Test thủ công 1 level

```bash
echo '{"x":1,"y":2,"channel":"R","value":128}' > body.json

echo "POST http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixel" | \
  ./vegeta attack -rate=1000 -duration=30s \
    -header="Content-Type: application/json" \
    -body=body.json \
    -workers=50 | \
  ./vegeta report
```

### Xem / xóa data

```bash
# Xem
curl http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixels

# Xóa
curl -X DELETE http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixels
```
