High-level overview of the system components, distinguishing between the Backend processing and the Frontend/BFF layers.

# 1. System Component Architecture

This diagram illustrates the decoupling of the high-performance backend from the lightweight user interface.

```mermaid
graph TB
    subgraph "External Sources"
        DM[(Data Marts)]
        DL[(Data Lakes)]
    end

    subgraph "Backend Processing Layer"
        IE[Ingestion Engine]
        DC[Data Comparator/Diff]
        AI[AI Attribution Service]
        DIS[The Discriminator]
    end

    subgraph "BFF Layer"
        IBFF[Identity & Audit BFF]
        RBFF[Recon & Operations BFF]
    end

    subgraph "Frontend"
        UI[Lightweight Reconciliation UI]
    end

    DM --> IE
    DL --> IE
    IE --> DC
    DC --> AI
    AI --> DIS
    
    ```markdown
    # 1. System Component Architecture (Updated)

    This diagram shows every independently running component in the `greenai` system and how they connect. Each box below represents a separately deployable process or container (examples in the repo: `frontend/`, `bff/`, `backend/*.py`, `database/`).

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
            Diff[diff_engine.py (Difference Engine)]
            Attr[attribution_engine.py (Attribution Engine)]
            Worker[Background Workers / Executors]
            Scheduler[(Scheduler / Cron)]
        end

        subgraph BFF[BFF Layer (API Facade)]
            BFF[bff (FastAPI) — `bff/main.py`]
        end

        subgraph Frontend[User Interface]
            UI[frontend (React/Vite) — ReconWorkstation]
        end

        subgraph Data[Datastores]
            PG[(PostgreSQL — primary DB)]
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
            K6[k6 (load tests) / scripts/load]
        end

        %% Flows
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

    Notes:
    - Each labeled item represents an independently running component (container, process, or service).
    - `ingest_engine.py`, `diff_engine.py`, `attribution_engine.py`, and background workers are separate processes and can be scaled independently.
    - `bff` is the API facade (FastAPI) that the `frontend` talks to; it reads from `PostgreSQL` and `Redis` and exposes `/metrics` and `/health`.
    - Observability (Prometheus/Grafana/Logs) and DevOps tooling are external but run independently and receive metrics/logs from the app components.
    ```

**Component → File mapping**
- `ingest_engine.py`: backend/ingest_engine.py
- `diff_engine.py`: backend/diff_engine.py
- `attribution_engine.py`: backend/attribution_engine.py
- `bff` (API): bff/main.py, bff/gunicorn_conf.py, bff/routers/
- `frontend` (UI): frontend/src/components/ReconWorkstation.tsx and frontend/src/
- `PostgreSQL` schema: database/schema/*.sql
- `Redis` used for queue/cache as configured in docker-compose.yml and scripts/run_staging_load.sh
- `k6` load test script: load/k6_test.js
