#!/usr/bin/env bash
# Container smoke checks for a built image (PLAN M3.4).
# Usage: scripts/container_smoke.sh [image]   (default: bvs:check)
# Needs docker, curl and openssl. Uses the dummy engine only; no model weights.
set -euo pipefail

IMAGE="${1:-bvs:check}"
PORT="${BVS_SMOKE_PORT:-8000}"
NAME="bvs-smoke-$$"

echo "== non-root user with writable /models and /data"
docker run --rm --network none --entrypoint /bin/sh "$IMAGE" -c \
  'test "$(id -u)" = 10001 && test -w /models && test -w /data'

echo "== packaged CLI, fonts and licence inside the image"
docker run --rm --network none "$IMAGE" --help > /dev/null
docker run --rm --network none --entrypoint python "$IMAGE" -c \
  "from importlib.resources import files; p = files('bvs.web') / 'static'; assert (p / 'fonts/NotoSansBengali.ttf').is_file(); assert (p / 'fonts/OFL.txt').is_file()"

echo "== offline dummy synthesis with egress blocked"
docker run --rm --network none -e BVS_TEST_MODE=1 "$IMAGE" \
  say 'আমি বাংলায় বলি।' --engine dummy --output /data/demo.wav --srt

echo "== broad binding without a token must refuse to start"
set +e
timeout 60 docker run --rm --network none "$IMAGE" serve --host 0.0.0.0
REFUSE_RC=$?
set -e
if [ "$REFUSE_RC" = 0 ] || [ "$REFUSE_RC" = 124 ]; then
  echo "Broad binding must refuse startup without a token (exit $REFUSE_RC)" >&2
  exit 1
fi

echo "== published port, health, authentication and packaged UI"
BVS_API_TOKEN="$(openssl rand -hex 32)"
export BVS_API_TOKEN
if [ -n "${GITHUB_ACTIONS:-}" ]; then echo "::add-mask::$BVS_API_TOKEN"; fi
docker run --detach --name "$NAME" -p "127.0.0.1:$PORT:8000" \
  -e BVS_API_TOKEN -e BVS_TEST_MODE=1 "$IMAGE" serve --demo --host 0.0.0.0 > /dev/null
cleanup() { docker logs "$NAME" 2>&1 | tail -n 40 || true; docker rm -f "$NAME" > /dev/null 2>&1 || true; }
trap cleanup EXIT
BASE="http://127.0.0.1:$PORT"
for _ in $(seq 1 60); do
  if curl --fail --silent "$BASE/health" > /dev/null; then break; fi
  sleep 0.5
done
curl --fail --silent "$BASE/health" > /dev/null
test "$(curl --silent -o /dev/null -w '%{http_code}' "$BASE/speak")" = 401
SHELL_HTML="$(curl --fail --silent --user "bvs:$BVS_API_TOKEN" "$BASE/speak")"
grep -q '/static/app.js' <<< "$SHELL_HTML"
curl --fail --silent -H "Authorization: Bearer $BVS_API_TOKEN" "$BASE/api/v1/engines" > /dev/null
curl --fail --silent --user "bvs:$BVS_API_TOKEN" "$BASE/static/fonts/OFL.txt" > /dev/null

echo "== graceful stop on SIGTERM (no SIGKILL after the grace period)"
START="$(date +%s)"
docker stop --time 10 "$NAME" > /dev/null
ELAPSED="$(( $(date +%s) - START ))"
EXIT_CODE="$(docker inspect --format '{{.State.ExitCode}}' "$NAME")"
echo "stopped in ${ELAPSED}s with exit code $EXIT_CODE"
if [ "$EXIT_CODE" = 137 ] || [ "$ELAPSED" -ge 10 ]; then
  echo 'Container ignored SIGTERM and had to be killed' >&2
  exit 1
fi

echo "== image size"
docker image inspect "$IMAGE" --format '{{.Size}}' | awk '{printf "image size: %.1f MB\n", $1 / 1000000}'
echo "container smoke passed"
