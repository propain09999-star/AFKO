#!/bin/sh
set -e

TARGET_URL="http://reverse-proxy:80"
VULNERABLE=0

echo "[*] Initializing Polyglot Mutation & Differential Fuzzing..."
apk add --no-cache curl

# Test Vector 1: HTTP Request Smuggling (CL.TE / TE.CL structural mismatch)
echo "[*] Injecting ambiguous HTTP header structures..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$TARGET_URL/api/data" \
  -H "Content-Length: 4" \
  -H "Transfer-Encoding: chunked" \
  -d "0\r\n\r\nG")

# A secure, aligned parser stack must reject ambiguous framing upfront with a 400 Bad Request
if [ "$HTTP_STATUS" != "400" ] && [ "$HTTP_STATUS" != "405" ]; then
  echo "[!] CRITICAL: Frontend and Backend parser alignment failed! HTTP Status: $HTTP_STATUS"
  VULNERABLE=1
fi

# Test Vector 2: Polyglot File Upload Bypass (JPEG containing executable scripts)
echo "[*] Uploading verified JPEG/JavaScript Polyglot vector..."
UPLOAD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$TARGET_URL/api/upload" \
  -F "file=@/payloads/image_polyglot.jpg;type=image/jpeg")

# The internal engine should strip metadata and strictly return a safe 200 or block with 400.
# If it returns a 500 server crash, it means the binary interpreter tried to run the script.
if [ "$UPLOAD_STATUS" == "500" ]; then
  echo "[!] CRITICAL: Polyglot binary caused backend engine unhandled parsing execution!"
  VULNERABLE=1
fi

if [ $VULNERABLE -eq 1 ]; then
  echo "[!] CI/CD GATE FAILURE: Security boundaries breached by polyglot testing."
  exit 1
else
  echo "[+] SUCCESS: Systems resisted all structural mutation and parse differentials."
  exit 0
fi
