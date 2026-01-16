```markdown
This script includes:

Schema Isolation: Creates a separate namespace (recon) to avoid collisions.

Data Integrity: Uses UUIDs for scalability, TIMESTAMPTZ for timezone-aware auditing, and strict FOREIGN KEY constraints.

Performance: Includes specific indices on high-cardinality columns used in joins and filtering.

Documentation: Includes SQL comments for column descriptions.
```

-- =============================================================================
-- RECONCILIATION SYSTEM CORE SCHEMA
-- Database: PostgreSQL 14+
-- Description: Core tables for runs, records, differences, and governance.
-- =============================================================================

-- 1. EXTENSIONS & SCHEMA
-- Enable UUID generation for non-sequential, scalable primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create specific schema to isolate reconciliation tables
CREATE SCHEMA IF NOT EXISTS recon;

-- =============================================================================
-- 2. REFERENCE TABLES
-- =============================================================================

-- Table: reason_codes
-- Purpose: Central repository for explanation codes (e.g., FX_VAR, MAN_ERR).
CREATE TABLE recon.reason_codes (
    reason_id           SERIAL PRIMARY KEY,
    code                VARCHAR(50) NOT NULL UNIQUE,
    description         TEXT NOT NULL,
    is_functional       BOOLEAN DEFAULT FALSE, -- TRUE = Business Logic, FALSE = Error
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE recon.reason_codes IS 'Configuration table for known difference reasons';

-- =============================================================================
-- 3. TRANSACTIONAL TABLES
-- =============================================================================

-- Table: recon_runs
-- Purpose: Tracks the execution of a reconciliation batch process.
CREATE TABLE recon.recon_runs (
    run_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_system_a     VARCHAR(100) NOT NULL,
    source_system_b     VARCHAR(100) NOT NULL,
    batch_date          DATE NOT NULL, -- The business date being reconciled
    start_time          TIMESTAMPTZ DEFAULT NOW(),
    end_time            TIMESTAMPTZ,
    status              VARCHAR(20) CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED', 'COMPLETED_WITH_ERRORS')),
    total_records       INTEGER DEFAULT 0,
    total_differences   INTEGER DEFAULT 0,
    metadata            JSONB -- Flexible field for config snapshots or runtime params
);

CREATE INDEX idx_runs_batch_date ON recon.recon_runs(batch_date);
CREATE INDEX idx_runs_status ON recon.recon_runs(status);

-- Table: recon_records
-- Purpose: Stores the raw linkage between two source records.
-- Note: In extremely high-volume systems, this table should be PARTITIONED by 'batch_date'.
CREATE TABLE recon.recon_records (
    record_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id              UUID NOT NULL REFERENCES recon.recon_runs(run_id) ON DELETE CASCADE,
    source_a_ref_id     VARCHAR(255), -- Primary Key from Source A
    source_b_ref_id     VARCHAR(255), -- Primary Key from Source B
    ingested_at         TIMESTAMPTZ DEFAULT NOW(),
    
    -- Storing normalized data as JSONB allows schema evolution without altering table structure
    normalized_data_a   JSONB, 
    normalized_data_b   JSONB
);

CREATE INDEX idx_records_run_id ON recon.recon_records(run_id);
CREATE INDEX idx_records_refs ON recon.recon_records(source_a_ref_id, source_b_ref_id);

-- Table: data_differences
-- Purpose: Specific field-level discrepancies found within a record.
CREATE TABLE recon.data_differences (
    diff_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_id           UUID NOT NULL REFERENCES recon.recon_records(record_id) ON DELETE CASCADE,
    field_name          VARCHAR(100) NOT NULL,
    value_a             TEXT, -- Cast to text for storage; type logic handled in app
    value_b             TEXT,
    diff_type           VARCHAR(50) NOT NULL, -- e.g., 'NUMERIC_PRECISION', 'STRING_MISMATCH'
    severity            VARCHAR(20) DEFAULT 'LOW' CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_diffs_record_id ON recon.data_differences(record_id);
CREATE INDEX idx_diffs_field_name ON recon.data_differences(field_name);

-- =============================================================================
-- 4. ATTRIBUTION & GOVERNANCE
-- =============================================================================

-- Table: attributions
-- Purpose: The "Brain" - stores the accepted reason for a difference.
CREATE TABLE recon.attributions (
    attribution_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    diff_id             UUID NOT NULL UNIQUE REFERENCES recon.data_differences(diff_id) ON DELETE CASCADE,
    reason_id           INTEGER REFERENCES recon.reason_codes(reason_id),
    
    -- AI Confidence Score (0.00 to 1.00)
    confidence_score    NUMERIC(5, 4) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    status              VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'UNKNOWN')),
    assigned_by         VARCHAR(50) DEFAULT 'SYSTEM', -- 'SYSTEM' or UserID
    assigned_at         TIMESTAMPTZ DEFAULT NOW(),
    is_locked           BOOLEAN DEFAULT FALSE -- If TRUE, requires 4-eye check to change
);

CREATE INDEX idx_attrib_status ON recon.attributions(status);
CREATE INDEX idx_attrib_confidence ON recon.attributions(confidence_score);

-- Table: audit_trail
-- Purpose: Immutable log of all human interactions (The 4-Eye Check Log).
CREATE TABLE recon.audit_trail (
    audit_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    attribution_id      UUID NOT NULL REFERENCES recon.attributions(attribution_id) ON DELETE CASCADE,
    actor_id            VARCHAR(100) NOT NULL, -- User ID or System Service Name
    action_type         VARCHAR(50) NOT NULL, -- 'OVERRIDE', 'APPROVE', 'REJECT', 'CREATE_REASON'
    previous_value      JSONB, -- Snapshot of data before change
    new_value           JSONB, -- Snapshot of data after change
    comments            TEXT,
    performed_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_attribution ON recon.audit_trail(attribution_id);
CREATE INDEX idx_audit_actor ON recon.audit_trail(actor_id);

-- =============================================================================
-- 5. UTILITY FUNCTION (UPDATED_AT)
-- =============================================================================

CREATE OR REPLACE FUNCTION recon.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_reason_codes_update
BEFORE UPDATE ON recon.reason_codes
FOR EACH ROW
EXECUTE PROCEDURE recon.update_timestamp();

```markdown
Key Design Decisions Explainers
JSONB for Data: In recon_records, we use JSONB for normalized_data.

Why: Reconciliation schemas change often. If Source A adds a new column, you don't want to run an ALTER TABLE command on a table with 50 million rows. JSONB allows you to ingest the new field immediately.

NUMERIC(5,4) for Confidence: This allows precision up to 0.9999 (99.99%), which is standard for ML confidence intervals.

Indices:

idx_attrib_confidence: Critical for the "Data Quality Gate" query (e.g., "Select all records where confidence < 0.8").

idx_records_refs: Critical for lookups if a user searches for a specific Trade ID or Transaction ID.

Audit Strategy: The audit_trail table stores previous_value and new_value as JSON snapshots. This allows you to reconstruct the exact state of a record at any point in time without complex temporal queries on the main table.
```