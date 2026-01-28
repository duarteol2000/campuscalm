#!/usr/bin/env bash
set -euo pipefail

API_HOST="${API_HOST:-http://localhost:8000}"
EMAIL="${API_EMAIL:-nari.naluu@gmail.com}"
PASSWORD="${API_PASSWORD:-Pucca&garu@20}"

login_response=$(curl -s -X POST "${API_HOST}/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")

access=$(printf '%s' "$login_response" | python3 - <<'PY'
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get("access", ""))
except Exception:
    print("", end="")
PY
)

if [ -z "$access" ]; then
  echo "Falha no login. Resposta:" >&2
  echo "$login_response" >&2
  exit 1
fi

bearer="Authorization: Bearer $access"

echo "== /api/auth/me/"
curl -s -H "$bearer" "${API_HOST}/api/auth/me/" | python3 -m json.tool

echo "== /api/mood/entries/"
curl -s -H "$bearer" "${API_HOST}/api/mood/entries/" | python3 -m json.tool

echo "== /api/planner/tasks/"
curl -s -H "$bearer" "${API_HOST}/api/planner/tasks/" | python3 -m json.tool

echo "== /api/agenda/week/"
curl -s -H "$bearer" "${API_HOST}/api/agenda/week/" | python3 -m json.tool

echo "== /api/semester/courses/"
course_list=$(curl -s -H "$bearer" "${API_HOST}/api/semester/courses/")
course_id=$(printf '%s' "$course_list" | python3 - <<'PY'
import json, sys
try:
    data = json.load(sys.stdin)
    if data:
        print(data[0].get("id", ""))
except Exception:
    print("")
PY
)

echo "$course_list" | python3 -m json.tool

if [ -n "$course_id" ]; then
  echo "== /api/semester/courses/${course_id}/progress/"
  curl -s -H "$bearer" "${API_HOST}/api/semester/courses/${course_id}/progress/" | python3 -m json.tool
fi

echo "== /api/content/guided/"
curl -s -H "$bearer" "${API_HOST}/api/content/guided/" | python3 -m json.tool

echo "== /api/onboarding/status/"
curl -s -H "$bearer" "${API_HOST}/api/onboarding/status/" | python3 -m json.tool

echo "== /api/analytics/dashboard/"
curl -s -H "$bearer" "${API_HOST}/api/analytics/dashboard/" | python3 -m json.tool
