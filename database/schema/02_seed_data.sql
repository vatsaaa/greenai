-- =============================================================================
-- SEED DATA: REASON CODES
-- Database: PostgreSQL
-- Description: Populates standard financial reconciliation reason codes.
--              Includes both Functional (Business) and Non-Functional (Error) codes.
-- =============================================================================

-- 1. FUNCTIONAL REASONS (Business Logic / Expected Differences)
--    These are usually candidates for Straight Through Processing (STP) if confidence is high.

INSERT INTO recon.reason_codes (code, description, is_functional, is_active)
VALUES 
    (
        'FX_VARIANCE', 
        'Difference attributed to exchange rate fluctuations between transaction capture times.', 
        TRUE, 
        TRUE
    ),
    (
        'TIMING_LAG', 
        'Timing difference due to distinct system cut-off times (e.g., T+0 vs T+1 booking).', 
        TRUE, 
        TRUE
    ),
    (
        'ROUNDING_DIFF', 
        'Immaterial difference caused by decimal precision logic (e.g., 2 vs 4 decimal places).', 
        TRUE, 
        TRUE
    ),
    (
        'PRICE_FLUCTUATION', 
        'Variance due to intraday market price movements between Source A and Source B snapshots.', 
        TRUE, 
        TRUE
    ),
    (
        'ACCRUAL_DIFF', 
        'Difference in interest accrual calculation methodologies (e.g., 30/360 vs Actual/360).', 
        TRUE, 
        TRUE
    ),
    (
        'SYSTEM_CONVERSION', 
        'Expected variance due to legacy data migration or currency redenomination logic.', 
        TRUE, 
        TRUE
    )
ON CONFLICT (code) DO NOTHING;


-- 2. NON-FUNCTIONAL REASONS (Errors / Exceptions)
--    These require Human-in-the-Loop (HITL) review or correction.

INSERT INTO recon.reason_codes (code, description, is_functional, is_active)
VALUES 
    (
        'MANUAL_ENTRY_ERR', 
        'Discrepancy likely caused by manual data entry error (e.g., typos, transposition).', 
        FALSE, 
        TRUE
    ),
    (
        'DATA_TYPE_MISMATCH', 
        'Technical error where fields are incompatible (e.g., String in a Numeric field).', 
        FALSE, 
        TRUE
    ),
    (
        'MISSING_SOURCE_A', 
        'Record exists in Source B but is completely missing from Source A.', 
        FALSE, 
        TRUE
    ),
    (
        'MISSING_SOURCE_B', 
        'Record exists in Source A but is completely missing from Source B.', 
        FALSE, 
        TRUE
    ),
    (
        'DUPLICATE_ENTRY', 
        'Multiple records found in one source matching a single record in the other.', 
        FALSE, 
        TRUE
    ),
    (
        'TRUNCATION_ERR', 
        'Data values appear cut off due to field length limitations in one source.', 
        FALSE, 
        TRUE
    )
ON CONFLICT (code) DO NOTHING;


-- 3. SYSTEM DEFAULT REASONS
--    Used by the AI engine when no specific pattern can be determined.

INSERT INTO recon.reason_codes (code, description, is_functional, is_active)
VALUES 
    (
        'UNKNOWN', 
        'The AI Attribution Engine could not determine a cause with sufficient confidence.', 
        FALSE, 
        TRUE
    ),
    (
        'PENDING_INVESTIGATION', 
        'Manually assigned status indicating the record is currently under deep review.', 
        FALSE, 
        TRUE
    )
ON CONFLICT (code) DO NOTHING;

-- =============================================================================
-- END OF SEED SCRIPT
-- =============================================================================
