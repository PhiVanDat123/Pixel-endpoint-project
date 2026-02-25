#!/bin/bash
# Script test throughput bằng vegeta
# Chạy trên máy c5

ENDPOINT="http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixel"
PIXELS_ENDPOINT="http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixels"
DURATION=30s

echo '{"x":1,"y":2,"channel":"R","value":128}' > body.json

for RATE in 100 200 500 1000 2000 5000; do
  echo "==============================="
  echo "Testing $RATE req/s for $DURATION..."
  echo "==============================="

  echo "POST $ENDPOINT" | \
    ./vegeta attack \
      -rate=$RATE \
      -duration=$DURATION \
      -header="Content-Type: application/json" \
      -body=body.json \
      -workers=50 \
      -max-connections=500 | \
    ./vegeta report --type=text

  echo ""
  echo ">> Store size sau test:"
  curl -s "$PIXELS_ENDPOINT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  total pixels: {d[\"total\"]}')"

  echo ">> Clearing stored pixels..."
  curl -s -X DELETE "$PIXELS_ENDPOINT" | python3 -m json.tool
  echo ""

  # Nghỉ 2s giữa các level để upstream recover
  sleep 2
done

rm -f body.json