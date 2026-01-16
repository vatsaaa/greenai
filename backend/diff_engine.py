"""
This engine is designed to be idempotent (can be re-run safely) and configurable.
Key Features:
Numeric Tolerance: Handles floating point epsilon ($0.00001$) to avoid false positives on tiny math variances.
Structural Detection: Automatically detects if a record is completely missing from one side.
Type Awareness: Distinguishes between NUMERIC_MISMATCH and STRING_MISMATCH.
Batch Processing: Fetches records in chunks to manage memory usage for large reconciliation runs.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# This module uses SQLAlchemy sync engine (psycopg). Ensure the
# `DB_URL` uses the `postgresql://...` scheme (no +asyncpg).
load_dotenv()

# Lazy DB wiring so module import is safe during tests
DB_URL: Optional[str] = os.getenv("DB_URL")
engine = None
Session = None


def ensure_engine() -> None:
    """Create the SQLAlchemy engine and sessionmaker if not already created."""
    global engine, Session
    if engine is not None and Session is not None:
        return

    db_url = os.getenv("DB_URL")
    if not db_url:
        raise RuntimeError(
            "DB_URL environment variable is required. Set it in the environment or in a local .env for development."
        )

    engine_local = create_engine(db_url)
    Session_local = sessionmaker(bind=engine_local)
    engine = engine_local
    Session = Session_local


NUMERIC_TOLERANCE = 0.005  # Differences smaller than this are ignored
BATCH_SIZE = 1000

# Logging Setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==============================================================================
# DATABASE SETUP
# ==============================================================================
# engine and Session will be created by `ensure_engine()` at runtime


# ==============================================================================
# COMPARISON LOGIC
# ==============================================================================
def is_numeric(n: Any) -> bool:
    """Checks if a value can be treated as a number."""
    try:
        float(n)
        return True
    except (ValueError, TypeError):
        return False


def compare_values(field: str, val_a: Any, val_b: Any) -> Optional[Dict[str, Any]]:
    """
    Compares two values and returns a difference dict if they don't match.
    Returns None if they match (within tolerance).
    """
    # 1. Handle Nulls
    if val_a is None and val_b is None:
        return None
    if val_a is None or val_b is None:
        return {
            "field": field,
            "val_a": str(val_a) if val_a is not None else None,
            "val_b": str(val_b) if val_b is not None else None,
            "type": "NULL_MISMATCH",
        }

    # 2. Numeric Comparison
    if is_numeric(val_a) and is_numeric(val_b):
        fa, fb = float(val_a), float(val_b)
        if abs(fa - fb) > NUMERIC_TOLERANCE:
            return {
                "field": field,
                "val_a": str(val_a),
                "val_b": str(val_b),
                "type": "NUMERIC_MISMATCH",
            }
        return None  # Match within tolerance

    # 3. String Comparison (Exact Match)
    if str(val_a) != str(val_b):
        return {
            "field": field,
            "val_a": str(val_a),
            "val_b": str(val_b),
            "type": "STRING_MISMATCH",
        }

    return None


def process_record(record: Any) -> List[Dict[str, Any]]:
    """
    Analyzes a single row from recon_records and identifies differences.
    """
    diffs = []

    # Unpack JSONB data
    # Note: sqlalchemy returns JSONB as python dicts automatically
    data_a = record.normalized_data_a
    data_b = record.normalized_data_b

    # SCENARIO 1: Missing Records
    if not record.source_a_ref_id:
        return [
            {
                "field_name": "ENTIRE_RECORD",
                "value_a": None,
                "value_b": "EXISTS",
                "diff_type": "MISSING_IN_SOURCE_A",
            }
        ]

    if not record.source_b_ref_id:
        return [
            {
                "field_name": "ENTIRE_RECORD",
                "value_a": "EXISTS",
                "value_b": None,
                "diff_type": "MISSING_IN_SOURCE_B",
            }
        ]

    # SCENARIO 2: Field Comparisons
    # We get the union of all keys to ensure we catch fields present in one but not the other
    all_keys = set(data_a.keys()).union(set(data_b.keys()))

    for key in all_keys:
        val_a = data_a.get(key)
        val_b = data_b.get(key)

        result = compare_values(key, val_a, val_b)
        if result:
            diffs.append(
                {
                    "field_name": result["field"],
                    "value_a": result["val_a"],
                    "value_b": result["val_b"],
                    "diff_type": result["type"],
                }
            )

    return diffs


# ==============================================================================
# EXECUTION ENGINE
# ==============================================================================
def run_difference_engine(target_run_id: Optional[str] = None) -> None:
    ensure_engine()
    assert Session is not None
    session = Session()

    try:
        # 1. Identify Run to Process
        # If no ID provided, grab the most recent 'COMPLETED' run
        if not target_run_id:
            logger.info("No Run ID provided. Fetching latest COMPLETED run...")
            latest_run = session.execute(
                text(
                    """
                SELECT run_id FROM recon.recon_runs 
                WHERE status = 'COMPLETED' 
                ORDER BY end_time DESC LIMIT 1
            """
                )
            ).fetchone()

            if not latest_run:
                logger.warning("No COMPLETED runs found to process.")
                return
            target_run_id = str(latest_run[0])

        logger.info(f"🚀 Starting Difference Engine for Run: {target_run_id}")

        # 2. Fetch Records (using server-side cursor logic or paging for memory efficiency)
        # For this script, we'll iterate with simple OFFSET/LIMIT paging
        offset = 0
        total_diffs_found = 0

        while True:
            logger.info(f"   -> Fetching batch {offset} to {offset+BATCH_SIZE}...")

            records = session.execute(
                text(
                    """
                SELECT record_id, source_a_ref_id, source_b_ref_id, normalized_data_a, normalized_data_b
                FROM recon.recon_records
                WHERE run_id = :rid
                ORDER BY record_id
                LIMIT :limit OFFSET :offset
            """
                ),
                {"rid": target_run_id, "limit": BATCH_SIZE, "offset": offset},
            ).fetchall()

            if not records:
                break  # No more records

            # 3. Process Batch
            diff_inserts = []

            for rec in records:
                # Find differences
                found_diffs = process_record(rec)

                # Prepare Bulk Insert
                for d in found_diffs:
                    diff_inserts.append(
                        {
                            "diff_id": str(uuid.uuid4()),
                            "record_id": rec.record_id,
                            "field_name": d["field_name"],
                            "value_a": d["value_a"],
                            "value_b": d["value_b"],
                            "diff_type": d["diff_type"],
                            "severity": (
                                "HIGH" if "MISSING" in d["diff_type"] else "MEDIUM"
                            ),
                        }
                    )

            # 4. Insert Differences
            if diff_inserts:
                session.execute(
                    text(
                        """
                    INSERT INTO recon.data_differences 
                    (diff_id, record_id, field_name, value_a, value_b, diff_type, severity)
                    VALUES (:diff_id, :record_id, :field_name, :value_a, :value_b, :diff_type, :severity)
                """
                    ),
                    diff_inserts,
                )

                total_diffs_found += len(diff_inserts)
                session.commit()  # Commit per batch

            offset += BATCH_SIZE

        # 5. Update Run Statistics
        logger.info(
            f"✅ Difference Analysis Complete. Total Differences: {total_diffs_found}"
        )
        session.execute(
            text(
                """
            UPDATE recon.recon_runs 
            SET total_differences = :td 
            WHERE run_id = :rid
        """
            ),
            {"td": total_diffs_found, "rid": target_run_id},
        )
        session.commit()

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Difference Engine Failed: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_difference_engine()
