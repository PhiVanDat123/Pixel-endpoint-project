# Pixel Endpoint Server

HTTP server nhận request mô tả pixel của ảnh, chạy trên 2 EC2 instance với Nginx làm Load Balancer.

## Kiến trúc

```
Client
  ↓
c5.xlarge:8000 (Nginx - Load Balancer)
  ↓                    ↓
c5.xlarge:8001      t2.xlarge:8000
(uvicorn app)       (uvicorn app)
```

## Thông tin máy chủ

| Instance | Type | Vai trò | Host |
|----------|------|---------|------|
| c5 | c5.xlarge | Load Balancer + App | ec2-3-235-128-192.compute-1.amazonaws.com |
| t2 | t2.xlarge | App | ec2-54-160-220-199.compute-1.amazonaws.com |

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
├── nginx/
│   └── pixel.conf       # Nginx load balancer config
├── test/
│   └── run_test.sh      # Script test throughput
└── README.md
```

---

## API Endpoints

### POST /pixel
Nhận request mô tả 1 pixel.

**Request body:**
```json
{
  "x": 10,
  "y": 20,
  "channel": "R",
  "value": 128
}
```

| Field | Type | Mô tả |
|-------|------|-------|
| x | int | Toạ độ x |
| y | int | Toạ độ y |
| channel | string | R, G, hoặc B |
| value | int | Giá trị pixel (0-255) |

**Response:**
```json
{"status": "ok"}
```

### GET /pixels
Trả về toàn bộ pixel đã nhận.

**Response:**
```json
{
  "total": 3000,
  "data": [
    {"x": 1, "y": 2, "channel": "R", "value": 128},
    ...
  ]
}
```

### DELETE /pixels
Xóa toàn bộ pixel đã lưu.

**Response:**
```json
{"status": "cleared"}
```

### GET /health
Health check endpoint.

**Response:**
```json
{"status": "healthy"}
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

### 2. Chạy app trên t2 (port 8000, bind private IP)

```bash
source venv/bin/activate
uvicorn main:app --host 172.31.25.176 --port 8000 &
```

> Thay `172.31.25.176` bằng private IP của t2 (`hostname -I`)

### 3. Chạy app trên c5 (port 8001)

```bash
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001 &
```

### 4. Cài và cấu hình Nginx trên c5

```bash
sudo apt install nginx -y

# Copy config
sudo cp nginx/pixel.conf /etc/nginx/sites-available/pixel
sudo ln -s /etc/nginx/sites-available/pixel /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Kiểm tra và restart
sudo nginx -t
sudo systemctl restart nginx
```

> Sửa private IP của t2 trong `nginx/pixel.conf` nếu khác `172.31.25.176`

---

## Hướng dẫn Test Throughput

### Cài vegeta

```bash
wget https://github.com/tsenart/vegeta/releases/download/v12.11.1/vegeta_12.11.1_linux_amd64.tar.gz
tar -zxvf vegeta_12.11.1_linux_amd64.tar.gz
```

### Test thủ công từng level

```bash
echo '{"x":1,"y":2,"channel":"R","value":128}' > body.json

# 100 req/s
echo "POST http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixel" | \
  ./vegeta attack -rate=100 -duration=30s \
    -header="Content-Type: application/json" \
    -body=body.json | \
  ./vegeta report
```

### Chạy script test tự động (100 → 5000 req/s)

```bash
chmod +x test/run_test.sh
./test/run_test.sh
```

### Xem data đã lưu

```bash
curl http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixels
```

### Xóa data

```bash
curl -X DELETE http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixels
