#!/bin/bash
# Script test throughput bằng vegeta
# Chạy trên máy c5

ENDPOINT="http://ec2-3-235-128-192.compute-1.amazonaws.com:8000/pixel"

echo '{"x":1,"y":2,"channel":"R","value":128}' > body.json

for RATE in 100 200 500 1000 2000 5000; do
  echo "==============================="
  echo "Testing $RATE req/s..."
  echo "==============================="

  echo "POST $ENDPOINT" | \
    ./vegeta attack -rate=$RATE -duration=30s \
      -header="Content-Type: application/json" \
      -body=body.json | \
    ./vegeta report

  echo ""
  echo ">> Clearing stored pixels..."
  curl -s -X DELETE $ENDPOINT/../pixels | python3 -m json.tool
  echo ""
done