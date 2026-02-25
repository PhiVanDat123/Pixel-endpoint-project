# gunicorn.conf.py
import multiprocessing

# 2x vCPU + 1 là công thức chuẩn cho I/O-bound workload
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"

# Giới hạn request mỗi worker trước khi restart (tránh memory leak)
max_requests = 10000
max_requests_jitter = 1000

# Timeout
timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "warning"   # production: chỉ log warning+, tắt access log để giảm I/O

# Worker tuning
worker_connections = 1000