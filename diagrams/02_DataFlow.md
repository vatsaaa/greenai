Represents the physical journey of a data record from the moment it is pulled from a source to its final storage in the 3rd Normal Form database.



# 2. End-to-End Data Flow

Detailed view of the "Straight Through Processing" (STP) vs. Exception handling paths.

```mermaid
graph LR
    Start(Data Source) --> Map[Field Mapping & Normalization]
    Map --> Diff{Difference Engine}
    
    Diff -- Match --> Gate[Data Quality Gate]
    Diff -- Mismatch --> Classify[Functional vs Non-Functional]
    
    Classify --> Predict[AI Attribution Prediction]
    
    Predict -- Confidence > 90% --> Gate
    Predict -- Confidence < 90% --> UI[Human Review/UNKNOWN]
    
    UI -- Approve --> Gate
    Gate --> Output[(3NF Performant Database)]
    UI -- Reject --> End[Data Rejected]
```markdown
End-to-end data flow mapping showing which independently running components handle each stage.

# 2. End-to-End Data Flow (Updated)

```mermaid
flowchart LR
    subgraph Sources[External Sources]
        A[Data Lake / File Drops]
        B[Data Mart / S3]
        C[External API]
    end

    IE[ingest_engine.py] -->|normalize| Map[Field Mapping & Normalization]
    A --> IE
    B --> IE
    C --> IE

    Map --> Diff[diff_engine.py (Difference Engine)]
    Diff -->|match| Gate[Data Quality Gate]
    Diff -->|mismatch| Classify[Classifier / Attribution Queue]

    subgraph Attribution[Attribution Path]
        AttrSvc[attribution_engine.py]
        Worker[Background Workers]
    end

    Classify --> AttrSvc
    AttrSvc -->|high confidence| Gate
    AttrSvc -->|low confidence| UI[frontend / Human Review]

    UI -->|review/override| BFF[bff (FastAPI)]
    BFF --> PG[(PostgreSQL)]
    Gate --> PG

    %% Training / Observability
    UI -->|corrections| TrainLog[(Training Log / Audit DB)]
    TrainLog --> ModelTrainer[(Model Training Service)]
    ModelTrainer --> ModelRegistry[(Model Registry)]

    %% Queues and cache
    Worker -->|cache| REDIS[(Redis)]
    BFF -->|cache reads| REDIS

    %% Load testing
    K6[k6 scripts] -->|simulate| BFF

    classDef datastore fill:#fef3c7,stroke:#f59e0b;
    class PG,REDIS,TrainLog datastore;

```

Notes:
- In production, `ingest_engine`, `diff_engine`, `attribution_engine`, and `Worker` are independent processes or containers.
- Human review flows go from `frontend` → `bff` → `PostgreSQL` and back into training logs so the learning pipeline can consume corrections asynchronously.
```

**Component → File mapping**
- `ingest_engine.py`: backend/ingest_engine.py
- `diff_engine.py`: backend/diff_engine.py
- `attribution_engine.py`: backend/attribution_engine.py
- `Worker` (background): backend/ (workers invoked from scripts or job runners)
- `BFF` (API): bff/main.py
- `Frontend`: frontend/src/
