import uuid
import pandas as pd
import logging
from typing import Dict, Tuple, Any, Optional
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import sessionmaker, Session as SyncSession

# Defer engine/session creation to runtime so importing this module in tests
# doesn't require a live `DB_URL` environment variable. Tests can import
# `AttributionModel` without DB access; the engine is constructed only when
# `run_attribution_engine()` is invoked.

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# This module uses SQLAlchemy sync engine (psycopg). Ensure the
# `DB_URL` uses the `postgresql://...` scheme (no +asyncpg).
load_dotenv()
DB_URL: Optional[str] = os.getenv("DB_URL")
# Lazy engine/session placeholder
engine: Optional[Engine] = None
Session: Optional[sessionmaker[SyncSession]] = None


def ensure_engine() -> None:
    """Create the SQLAlchemy engine and sessionmaker if not already created."""
    global engine, Session, DB_URL

    if engine is not None and Session is not None:
        return

    DB_URL = os.getenv("DB_URL")
    if not DB_URL:
        raise RuntimeError(
            "DB_URL environment variable is required. Set it in the environment or in a local .env for development."
        )

    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)


CONFIDENCE_THRESHOLD = 0.85  # Below this, we flag as UNKNOWN

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Engine and Session are created lazily by `ensure_engine()` at runtime.


# ==============================================================================
# REASON CODE MAPPER (Cache)
# ==============================================================================
def get_reason_map(session: Any) -> Dict[str, int]:
    """Fetches reason codes from DB to map string codes to IDs."""
    result = session.execute(
        text("SELECT code, reason_id FROM recon.reason_codes")
    ).fetchall()
    return {row[0]: row[1] for row in result}


# ==============================================================================
# HYBRID AI LOGIC
# ==============================================================================
class AttributionModel:
    def __init__(self, reason_map: Dict[str, int]):
        self.reason_map: Dict[str, int] = reason_map
        # In a real PROD system, we would load a trained .pkl model here
        # self.model = joblib.load('models/attribution_v1.pkl')
        self.model = None

    def predict(self, diff_record: pd.Series) -> Tuple[Optional[int], float]:
        """
        Returns (reason_id, confidence_score)
        """
        d_type = diff_record["diff_type"]
        val_a = diff_record["value_a"]
        val_b = diff_record["value_b"]

        # --- RULE BASED LOGIC (Deterministic) ---

        # 1. Missing Records
        if d_type == "MISSING_IN_SOURCE_A":
            return self.reason_map.get("MISSING_SOURCE_A"), 1.0
        if d_type == "MISSING_IN_SOURCE_B":
            return self.reason_map.get("MISSING_SOURCE_B"), 1.0

        # 2. Data Type Mismatches
        if d_type == "TYPE_MISMATCH":
            return self.reason_map.get("DATA_TYPE_MISMATCH"), 1.0

        # --- HEURISTIC / ML SIMULATION LOGIC ---

        # 3. Numeric Variances
        if d_type == "NUMERIC_MISMATCH":
            try:
                # Feature Engineering: Calculate Magnitude
                va = float(val_a) if val_a else 0.0
                vb = float(val_b) if val_b else 0.0
                delta = abs(va - vb)

                # Heuristic A: Small Rounding Errors
                if delta < 0.02:
                    return self.reason_map.get("ROUNDING_DIFF"), 0.98

                # Heuristic B: Percentage-based FX Variance
                # If variance is roughly standard FX movement (e.g. ~1-2%)
                pct_diff = delta / va if va != 0 else 0
                if 0.005 < pct_diff < 0.03:
                    return self.reason_map.get("FX_VARIANCE"), 0.88

            except Exception:
                pass

        # 4. String Variances
        if d_type == "STRING_MISMATCH":
            # Heuristic C: Typos (e.g. "Inc" vs "Inc.")
            # In a real model, we would use Levenshtein distance here
            if val_a and val_b:
                str_a = str(val_a).replace(".", "").replace(",", "").strip()
                str_b = str(val_b).replace(".", "").replace(",", "").strip()
                if str_a == str_b:
                    return self.reason_map.get("MANUAL_ENTRY_ERR"), 0.90

        # --- FALLBACK (The Unknown) ---
        return self.reason_map.get("UNKNOWN"), 0.0


# ==============================================================================
# BATCH EXECUTION
# ==============================================================================
def run_attribution_engine() -> None:
    ensure_engine()
    assert Session is not None
    session = Session()
    try:
        logger.info("🤖 Starting AI Attribution Engine...")

        # 1. Load Dependencies
        reason_map = get_reason_map(session)
        ai_model = AttributionModel(reason_map)

        # 2. Fetch Unprocessed Differences
        # We join with attributions to find diffs that don't have an attribution yet
        logger.info("   -> Fetching pending differences...")
        sql = """
            SELECT d.diff_id, d.diff_type, d.field_name, d.value_a, d.value_b 
            FROM recon.data_differences d
            LEFT JOIN recon.attributions a ON d.diff_id = a.diff_id
            WHERE a.attribution_id IS NULL
            LIMIT 5000
        """
        # Load into Pandas for efficient vectorization if needed later
        df_diffs = pd.read_sql(sql, session.connection())

        if df_diffs.empty:
            logger.info("   -> No pending differences found.")
            return

        logger.info(f"   -> Processing {len(df_diffs)} records...")

        # 3. Predict Loop
        attributions_to_insert = []

        for _, row in df_diffs.iterrows():
            reason_id, confidence = ai_model.predict(row)

            # Determine Status
            status = "ACCEPTED" if confidence >= CONFIDENCE_THRESHOLD else "UNKNOWN"

            attributions_to_insert.append(
                {
                    "attribution_id": str(uuid.uuid4()),
                    "diff_id": row["diff_id"],
                    "reason_id": reason_id,
                    "confidence_score": confidence,
                    "status": status,
                    "assigned_by": "AI_ENGINE_V1",
                }
            )

        # 4. Bulk Insert
        if attributions_to_insert:
            logger.info(f"   -> Saving {len(attributions_to_insert)} attributions...")

            insert_sql = text(
                """
                INSERT INTO recon.attributions 
                (attribution_id, diff_id, reason_id, confidence_score, status, assigned_by)
                VALUES (:attribution_id, :diff_id, :reason_id, :confidence_score, :status, :assigned_by)
            """
            )

            session.execute(insert_sql, attributions_to_insert)
            session.commit()

            # 5. Summary Stats
            unknown_count = sum(
                1 for x in attributions_to_insert if x["status"] == "UNKNOWN"
            )
            logger.info("✅ Batch Complete.")
            logger.info(
                f"   - Auto-Resolved: {len(attributions_to_insert) - unknown_count}"
            )
            logger.info(f"   - Marked UNKNOWN: {unknown_count}")

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Attribution Engine Failed: {str(e)}")
    finally:
        session.close()


if __name__ == "__main__":
    run_attribution_engine()
