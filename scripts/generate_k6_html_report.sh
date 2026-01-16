#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SUMMARY_FILE="$ROOT_DIR/artifacts/load_test/summary.txt"
OUT_HTML="$ROOT_DIR/artifacts/load_test/report.html"

mkdir -p "$(dirname "$OUT_HTML")"

if [ ! -f "$SUMMARY_FILE" ]; then
  echo "Summary file not found: $SUMMARY_FILE" >&2
  exit 1
fi

# Extract metrics (best-effort parsing of k6 tail summary)
TOTAL_REQUESTS=$(grep -m1 "http_reqs" "$SUMMARY_FILE" | sed -n 's/.*http_reqs.*: *\([0-9]*\).*/\1/p' || true)
THROUGHPUT=$(grep -m1 "http_reqs" "$SUMMARY_FILE" | sed -n 's/.*http_reqs.*: *[0-9]* *\([0-9.]*\/s\).*/\1/p' || true)
LATENCY_LINE=$(grep -m1 "http_req_duration" "$SUMMARY_FILE" || true)
LATENCY_AVG=$(echo "$LATENCY_LINE" | sed -n 's/.*avg=\([^ ]*\).*/\1/p' || true)
LATENCY_P90=$(echo "$LATENCY_LINE" | sed -n 's/.*p(90)=\([^, ]*\).*/\1/p' || true)
LATENCY_P95=$(echo "$LATENCY_LINE" | sed -n 's/.*p(95)=\([^ ]*\).*/\1/p' || true)
ERRORS=$(grep -m1 "http_req_failed" "$SUMMARY_FILE" | sed -n 's/.*http_req_failed.*: *\([0-9.]*%\).*/\1/p' || true)

cat > "$OUT_HTML" <<HTML
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>k6 Full Load Test Report</title>
  <style>body{font-family:Inter,system-ui,Arial,sans-serif;padding:24px}pre{background:#111;color:#eee;padding:12px;overflow:auto}</style>
</head>
<body>
  <h1>k6 Full Load Test Report</h1>
  <p><strong>Source:</strong> artifacts/load_test/summary.txt</p>
  <h2>Key Metrics</h2>
  <ul>
    <li><strong>Total requests:</strong> ${TOTAL_REQUESTS:-n/a}</li>
    <li><strong>Throughput:</strong> ${THROUGHPUT:-n/a}</li>
    <li><strong>Avg latency:</strong> ${LATENCY_AVG:-n/a}</li>
    <li><strong>p(90):</strong> ${LATENCY_P90:-n/a}</li>
    <li><strong>p(95):</strong> ${LATENCY_P95:-n/a}</li>
    <li><strong>Errors:</strong> ${ERRORS:-n/a}</li>
  </ul>

  <h2>Raw k6 tail summary</h2>
  <pre>
$(sed 's/&/&amp;/g; s/</\&lt;/g; s/>/\&gt;/g' "$SUMMARY_FILE")
  </pre>
</body>
</html>
HTML

echo "Generated HTML report: $OUT_HTML"
exit 0
