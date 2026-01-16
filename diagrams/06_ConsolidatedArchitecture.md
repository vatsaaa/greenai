```markdown
# Consolidated System Architecture

This consolidated diagram shows every independently running component, their relationships, and the repository files that implement them.

```mermaid
flowchart TB
    subgraph External[External Systems]
        DL[Data Lakes / File Drops]
        DM[Data Marts / S3 / FTP]
        EX_API[External APIs]
    end

    subgraph Ingest[Ingestion Layer]
        IE[ingest_engine.py]
        Queue[(Redis / Work Queue)]
    end

    subgraph Backend[Backend Processing]
        Diff[diff_engine.py]
        Attr[attribution_engine.py]
        Worker[Background Workers / Executors]
        Scheduler[(Scheduler / Cron)]
    end

    subgraph BFF[BFF Layer]
        BFF[bff (FastAPI) — bff/main.py]
    end

    subgraph Frontend[User Interface]
        UI[frontend (React/Vite) — ReconWorkstation]
    end

    subgraph Data[Datastores]
        PG[(PostgreSQL — database/schema/*.sql)]
        REDIS[(Redis — cache/queue/session)]
    end

    subgraph Observability[Observability]
        Prom[Prometheus]
        Grafana[Grafana]
        Logs[Structured JSON Logs / Log Aggregator]
    end

    subgraph DevOps[Infra & Tools]
        Docker[Docker / Compose]
        K8s[Kubernetes / Helm]
        CI[GitHub Actions / CI pipelines]
        K6[k6 (load tests) / load/]
    end

    DL --> IE
    DM --> IE
    EX_API --> IE

    IE -->|push| Queue
    Queue --> Worker
    Worker --> Diff
    Diff --> Attr
    Attr --> PG
    Worker --> PG

    Scheduler --> Worker
    Worker -->|publish cache| REDIS

    PG --> BFF
    REDIS --> BFF
    BFF --> UI
    UI --> BFF

    BFF -->|metrics| Prom
    Worker -->|metrics| Prom
    BFF -->|logs| Logs
    Worker -->|logs| Logs

    CI --> Docker
    Docker --> K8s
    K6 -->|exercise| BFF

    classDef infra fill:#f3f4f6,stroke:#94a3b8;
    class Docker,K8s,CI,Prom,Grafana,Logs,K6 infra;

```

**Component → File mapping**
- `ingest_engine.py`: backend/ingest_engine.py
- `diff_engine.py`: backend/diff_engine.py
- `attribution_engine.py`: backend/attribution_engine.py
- `bff` (API): bff/main.py, bff/gunicorn_conf.py, bff/routers/
- `frontend` (UI): frontend/src/components/ReconWorkstation.tsx and frontend/src/
- `PostgreSQL` schema: database/schema/*.sql
- `Redis` used for queue/cache as configured in `docker-compose.yml` and `scripts/run_staging_load.sh`
- `k6` load test scripts: load/k6_test.js, load/k6_full_test.js

Notes:
- This consolidated diagram replaces prior mixed fragments and provides a single canonical mermaid diagram for documentation and export.

```
