**Purpose:** Visualizes the 4-eye/6-eye check process when a human intervenes to create a new reason or correct an attribution.


# 3. Human-in-the-Loop Workflow

This represents the governance process for managing "UNKNOWN" differences and new reason creation.

```mermaid
sequenceDiagram
    autonumber
    participant Maker as User (Maker)
    participant Sys as AI System
    participant Checker as Supervisor (Checker)
    participant DB as Knowledge Base

    Maker->>Sys: Selects 'UNKNOWN' record
    Sys->>Maker: Displays Top 3 Predictions
    Maker->>Sys: Overrides with New Reason
    Sys->>Checker: Move to Review Queue (4-eye Check)
    
    alt Approved
        Checker->>Sys: Authorize Change
        Sys->>DB: Update Historical Attribution File
        Sys->>Maker: Record Resolved
    else Rejected
        Checker->>Maker: Send back for Correction
    ```markdown
    **Purpose:** Visualizes the 4-eye/6-eye check process when a human intervenes to create a new reason or correct an attribution.

    # 3. Human-in-the-Loop Workflow (Updated)

    Shows the user, frontend, BFF, background workers and the DB as independent components.

    ```mermaid
    sequenceDiagram
        autonumber
        participant Maker as User (Maker)
        participant UI as Frontend (React)
        participant API as BFF (FastAPI)
        participant Worker as Background Worker / Attribution Engine
        participant Checker as Supervisor (Checker)
        participant DB as PostgreSQL

        Maker->>UI: Selects 'UNKNOWN' record
        UI->>API: GET /records/{id}
        API->>DB: fetch record + predictions
        DB-->>API: return data
        API-->>UI: render predictions

        Maker->>UI: Override / create new reason
        UI->>API: POST /records/{id}/override
        API->>DB: insert audit & training log
        API->>Worker: enqueue correction (background)

        Worker->>Checker: add to review queue
        alt Approved
            Checker->>API: approve via UI
            API->>DB: update attribution history
        else Rejected
            Checker->>Maker: Send back for correction
        end
    ```

    Notes:
    - `UI`, `API`, `Worker`, and `DB` are independently running components; the UI talks only to the BFF API.
    ```

    **Component → File mapping**
    - `UI` (Frontend): frontend/src/components/ReconWorkstation.tsx
    - `API` (BFF): bff/main.py and bff/routers/
    - `Worker` (Attribution/Background): backend/attribution_engine.py
    - `DB` (Postgres schema): database/schema/*.sql

