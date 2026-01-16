**Purpose:** Shows the separation between the "Hot Path" (daily execution) and the "Cold Path" (AI model retraining).


# 4. Execution vs. Learning Workflows

Architectural separation to ensure model training doesn't slow down the live reconciliation engine.

```mermaid
graph TD
    subgraph "Execution Workflow (Hot Path)"
        Run[Daily Recon Run]
        Inference[Apply 'Frozen' ML Model]
        Run --> Inference
    end

    subgraph "Learning Workflow (Cold Path)"
        Log[Capture Human Corrections]
        Train[Retrain Attribution Model]
        Test[Discriminator Validation]
        Log --> Train
        Train --> Test
    end

    Test -- Update --> Inference
    Inference -- Feedback --> Log
```markdown
**Purpose:** Shows separation between the Hot Path (live execution) and the Cold Path (training), and lists the independently running components involved in each.

# 4. Execution vs. Learning Workflows (Updated)

```mermaid
flowchart LR
    subgraph Hot[Execution Workflow (Hot Path)]
        Run[Daily Recon Run Service]
        Inference[Inference Service (uses frozen model)]
        Run --> Inference
        Inference -->|write results| PG[(PostgreSQL)]
        Inference -->|metrics| Prom[Prometheus]
    end

    subgraph Cold[Learning Workflow (Cold Path)]
        Log[Training Log / Audit DB]
        Trainer[Model Trainer (batch job)]
        Validator[Discriminator / Validation Service]
        ModelReg[Model Registry]
        Log --> Trainer
        Trainer --> Validator
        Validator --> ModelReg
    end

    ModelReg -->|release new model| Inference
    PG -->|human corrections| Log

    classDef infra fill:#eef2ff,stroke:#6366f1;
    class Prom,ModelReg infra;

```

Notes:
- `Run`, `Inference`, `Trainer`, `Validator`, and `ModelReg` are all independent processes/jobs and should be scheduled and scaled separately.
- The Hot Path must be low-latency and not be impacted by Cold Path training resource usage.
```

**Component → File mapping**
- `Run` / Reconciliation service: backend/diff_engine.py
- `Inference` / Serving: backend/attribution_engine.py (or a separate inference service)
- `Trainer`: training scripts / pipelines (not present as single file — captured in `backend/` and `scripts/`)
- `Model Registry`: external (not in repo)
