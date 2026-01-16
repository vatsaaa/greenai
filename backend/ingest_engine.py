import pandas as pd
import yaml
import uuid
import os
from dotenv import load_dotenv
import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, Optional

# ==============================================================================
# SETUP & LOGGING
# ==============================================================================
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load Environment Variables for Secrets (Best Practice)
load_dotenv()
DB_URL = os.getenv("DB_URL")
if not DB_URL:
    raise RuntimeError(
        "DB_URL environment variable is required. Set it in the environment or in a local .env for development."
    )
CONFIG_PATH = os.getenv("CONFIG_PATH", "backend/config/job_fx_trades.yaml")

engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)


# ==============================================================================
# 1. DATA SOURCE FACTORY
# ==============================================================================
class DataSourceFactory:
    """
    Decouples the logic of 'How to get data' from the main ingestion flow.
    """

    @staticmethod
    def fetch_data(source_config: Dict[str, Any]) -> pd.DataFrame:
        s_type = source_config.get("type", "").lower()
        conn = source_config.get("connection", {})

        logger.info(
            f"   -> Fetching data from {source_config['name']} (Type: {s_type})..."
        )

        if s_type == "csv":
            path = conn.get("path")
            if not os.path.exists(path):
                raise FileNotFoundError(f"CSV path not found: {path}")
            return pd.read_csv(path)

        elif s_type == "sql":
            # Support for database connections
            db_url = conn.get("connection_string")
            query = conn.get("query")

            # Simple variable substitution (e.g., injecting Batch Date)
            batch_date = datetime.now().strftime("%Y-%m-%d")
            query = query.replace("${BATCH_DATE}", batch_date)

            source_eng = create_engine(db_url)
            return pd.read_sql(query, source_eng)

        elif s_type == "parquet":
            return pd.read_parquet(conn.get("path"))

        else:
            raise ValueError(f"Unsupported source type: {s_type}")


# ==============================================================================
# 2. NORMALIZATION ENGINE
# ==============================================================================
def normalize_dataset(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Applies 1) Column Renaming (Mapping) and 2) Data Cleaning Rules
    """
    mapping = config.get("mapping", {})
    rules = config.get("normalization_rules", {})

    # 1. Filter & Rename Columns based on Config
    # We only keep columns defined in the mapping
    available_cols = [c for c in mapping.keys() if c in df.columns]
    df = df[available_cols].copy()
    df.rename(columns=mapping, inplace=True)

    # 2. Apply Rules
    if rules.get("uppercase_strings"):
        str_cols = df.select_dtypes(include=["object"]).columns
        for col in str_cols:
            df[col] = df[col].astype(str).str.strip().str.upper()

    # 3. Date Formatting
    # In a robust system, you'd specify which columns are dates in config
    # Here we assume 'trade_date' is canonical
    if "trade_date" in df.columns:
        fmt = rules.get("date_format", "%Y-%m-%d")
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime(fmt)

    return df


# ==============================================================================
# 3. MAIN EXECUTION FLOW
# ==============================================================================
def run_ingestion() -> None:
    session = Session()
    run_id = str(uuid.uuid4())

    try:
        # A. Load Configuration
        logger.info(f"🚀 Loading Job Config: {CONFIG_PATH}")
        with open(CONFIG_PATH, "r") as f:
            job_config = yaml.safe_load(f)

        # B. Initialize Run Record
        logger.info(f"   -> Job: {job_config['job_name']}")
        start_time = datetime.now()

        session.execute(
            text(
                """
            INSERT INTO recon.recon_runs 
            (run_id, source_system_a, source_system_b, batch_date, status, start_time, metadata)
            VALUES (:rid, :src_a, :src_b, :bdate, 'RUNNING', :stime, :meta)
        """
            ),
            {
                "rid": run_id,
                "src_a": job_config["source_a"]["name"],
                "src_b": job_config["source_b"]["name"],
                "bdate": datetime.today().date(),
                "stime": start_time,
                "meta": json.dumps({"config_used": CONFIG_PATH}),
            },
        )
        session.commit()

        # C. Fetch & Normalize Data (Driven by Config)
        # Combine Source A config + Global Rules
        cfg_a = job_config["source_a"]
        cfg_a["normalization_rules"] = job_config["normalization_rules"]

        cfg_b = job_config["source_b"]
        cfg_b["normalization_rules"] = job_config["normalization_rules"]

        df_a = DataSourceFactory.fetch_data(cfg_a)
        df_a = normalize_dataset(df_a, cfg_a)

        df_b = DataSourceFactory.fetch_data(cfg_b)
        df_b = normalize_dataset(df_b, cfg_b)

        # D. Alignment (Merge Strategy)
        # Note: Join keys should ideally come from config too.
        # For simplicity, we assume 'transaction_id' is the canonical key.
        logger.info("   -> Aligning Data...")
        df_a_tagged = df_a.add_suffix("_A")
        df_b_tagged = df_b.add_suffix("_B")

        merged_df = pd.merge(
            df_a_tagged,
            df_b_tagged,
            left_on="transaction_id_A",
            right_on="transaction_id_B",
            how="outer",
        )

        # E. Persist to DB
        logger.info("   -> preparing batch insert...")
        records_to_insert = []
        for _, row in merged_df.iterrows():
            # Helper to safely extract dict for JSONB
            def get_clean_dict(row_data: Dict[str, Any], suffix: str) -> Optional[str]:
                d = {
                    k.replace(suffix, ""): v
                    for k, v in row_data.items()
                    if k.endswith(suffix) and pd.notna(v)
                }
                return json.dumps(d) if d else None

            rec_a = get_clean_dict(row, "_A")
            rec_b = get_clean_dict(row, "_B")

            ref_a = row.get("transaction_id_A")
            ref_b = row.get("transaction_id_B")

            # Handle NaN/None for IDs
            if pd.isna(ref_a):
                ref_a = None
            if pd.isna(ref_b):
                ref_b = None

            records_to_insert.append(
                {
                    "record_id": str(uuid.uuid4()),
                    "run_id": run_id,
                    "source_a_ref_id": ref_a,
                    "source_b_ref_id": ref_b,
                    "normalized_data_a": rec_a,
                    "normalized_data_b": rec_b,
                }
            )

        # Bulk Insert
        if records_to_insert:
            session.execute(
                text(
                    """
                INSERT INTO recon.recon_records 
                (record_id, run_id, source_a_ref_id, source_b_ref_id, normalized_data_a, normalized_data_b)
                VALUES (:record_id, :run_id, :source_a_ref_id, :source_b_ref_id, :normalized_data_a, :normalized_data_b)
            """
                ),
                records_to_insert,
            )

        # F. Completion
        session.execute(
            text(
                """
            UPDATE recon.recon_runs 
            SET status = 'COMPLETED', end_time = NOW(), total_records = :total
            WHERE run_id = :rid
        """
            ),
            {"rid": run_id, "total": len(records_to_insert)},
        )
        session.commit()
        logger.info(f"✅ Ingestion Complete. Run ID: {run_id}")

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Ingestion Failed: {str(e)}")
        # Log failure to DB
        try:
            session.execute(
                text(
                    "UPDATE recon.recon_runs SET status = 'FAILED' WHERE run_id = :rid"
                ),
                {"rid": run_id},
            )
            session.commit()
        except Exception:
            pass
    finally:
        session.close()


if __name__ == "__main__":
    run_ingestion()
