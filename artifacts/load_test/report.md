# Full Load Test Report

Date: 2026-01-16

Test: `load/k6_full_test.js` — 200 VUs for 5 minutes

Summary metrics

- Total requests: 59,603
- Throughput: ~198 req/s
- Average latency: 6.35 ms
- p(90): 10.81 ms
- p(95): 12.42 ms
- Errors: 0.00%
- Duration: 5m
- VUs: 200 (vu_max=200)

Artifacts

- k6 raw outputs and logs: artifacts/load_test/*.txt
- brief k6 tail summary: artifacts/load_test/summary.txt

Notes

- k6 ran inside a Docker container attached to the `greenai-net` network targeting the `greenai-staging-bff` container.
- Postgres and Redis were started transiently for this run; the script tears them down at completion.
- No failed requests observed; latency is low for simple `/health` endpoint (see detailed logs).

Next steps

- Generate an HTML report from k6 JSON output (requires running k6 with `--out json=...`).
- Run multi-endpoint scenarios to exercise DB/ingest/attribution paths.
