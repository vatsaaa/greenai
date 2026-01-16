---
[ 📄 View System Requirements](../SystemRequirements.md) | [ 🏗️ View Architecture Diagrams](./01_SystemArchitecture.md)
---

_Diagrams updated to list every independently running component (frontend, bff, backend engines, workers, DBs, Redis, observability, CI/CD and load-test tooling)._ 

# AI-Enhanced Reconciliation System Framework

This repository contains the architectural blueprints and process flows for a high-performance data reconciliation system. The system is designed not just to find differences, but to **explain them** and act as a **Data Quality Gate** for downstream financial or operational systems.

## 1. Core Philosophy: The "Data Quality Gate"
The system operates on the principle that data should only move forward if its state is "Explained and Validated."
* **Auto-Pass:** Differences with a high-confidence "Functional" attribution (e.g., standard FX fluctuations) pass through the gate automatically.
* **Circuit Breaker:** Differences marked as "Unknown" or "Non-Functional" (Errors) halt the pipeline until a human-in-the-loop (HITL) review is completed.

## 2. Document Navigation
The following files provide the complete system breakdown:

| File | Title | Description |
| :--- | :--- | :--- |
| `01_SystemArchitecture.md` | **System Components** | Shows the separation between Backend services and BFF layers. |
| `02_DataFlow.md` | **End-to-End Flow** | Traces a record from ingestion to the 3rd Normal Form database. |
| `03_UserWorkflow.md` | **Human Governance** | Details the 4/6-eye check for manual overrides and new reasons. |
| `04_LearningVsExecution.md` | **AI Workflow Separation** | Explains how the system learns from humans without slowing down daily runs. |
| `05_DatabaseSchema.md` | **3NF Entity Relationship** | The performant data model for storage and trend analysis. |

## 3. AI Strategy
The system uses a **Hybrid AI approach**:
1. **Deterministic Logic:** Used for numeric comparison and precision variance.
2. **Simple Machine Learning (ML):** Used for classification and confidence scoring of known functional reasons.
3. **Generative AI (GenAI):** Used for interpreting unstructured metadata during initial field mapping and summarizing complex difference reports for human review.

## 4. Technical Stack Recommendations
* **Backend:** Go or Java (Spring Boot) for high-concurrency processing.
* **Database:** PostgreSQL (with JSONB for flexible metadata) or a Time-Series database like TimescaleDB for historical trend analysis.
* **BFF Layer:** Node.js or Python (FastAPI) to handle lightweight frontend requests and orchestration.
* **Frontend:** React or Vue.js, optimized for "Thin Client" operations.

## 5. Summary of Stages
1. **Ingest:** Pull from Data Lakes/Marts (Non-OLTP).
2. **Diff:** Identify mismatches across all data types.
3. **Attribute:** Predict reasons based on historical context.
4. **Govern:** Human review for "Unknowns" with multi-eye verification.
5. **Audit:** The Discriminator reviews system performance to prevent drift.

---
*Note: All diagrams in these files are rendered using Mermaid.js. Use a Markdown viewer with Mermaid support to visualize the flows.