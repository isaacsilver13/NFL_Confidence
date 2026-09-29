#!/usr/bin/env bash
# Wake the app (Fly auto-starts a stopped machine on an incoming request) and ask
# it to run whichever scheduled jobs are due. Retries cover a cold start.
#
# Required env: APP_BASE_URL (https://host, no trailing path), TICK_TOKEN
# Attempts at t=0s, t=20s and t=45s; each request waits up to 60s for the machine.
set -uo pipefail

: "${APP_BASE_URL:?APP_BASE_URL is required}"
: "${TICK_TOKEN:?TICK_TOKEN is required}"

base="${APP_BASE_URL%/}"
body="$(mktemp)"
delays=(0 20 25)
code=000

for attempt in 1 2 3; do
  sleep "${delays[$((attempt - 1))]}"
  echo "Attempt ${attempt}/3: waking ${base}"
  # A cheap request first: it starts a stopped machine and waits for the health check.
  curl -sS --max-time 60 -o /dev/null "${base}/api/v1/health" || echo "health probe did not succeed (machine may still be starting)"

  code="$(curl -sS --max-time 60 -o "$body" -w '%{http_code}' -X POST \
    -H "Authorization: Bearer ${TICK_TOKEN}" "${base}/api/v1/internal/tick")" || code=000
  echo "tick responded HTTP ${code}"

  if [ "$code" = "200" ]; then
    break
  fi
  # Wrong/missing token or an unconfigured app will not fix itself: don't retry.
  if [ "$code" = "401" ] || [ "$code" = "403" ] || grep -q TICK_DISABLED "$body" 2>/dev/null; then
    echo "::error::Tick rejected (HTTP ${code}); check TICK_TOKEN on the app and in GitHub secrets."
    break
  fi
done

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### Tick result (HTTP ${code})"
    echo '```json'
    if command -v jq >/dev/null 2>&1 && jq . "$body" 2>/dev/null; then :; else cat "$body"; fi
    echo '```'
  } >> "$GITHUB_STEP_SUMMARY"
fi

[ "$code" = "200" ] && exit 0
echo "::error::Tick failed after retries (last HTTP ${code})"
exit 1
