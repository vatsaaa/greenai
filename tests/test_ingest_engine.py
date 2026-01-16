import pandas as pd
from backend.ingest_engine import normalize_dataset


def test_normalize_dataset_mapping_and_dates():
    df = pd.DataFrame([{"txn_id": "1", "trade_date": "2025-01-01", "name": " alice "}])

    config = {
        "mapping": {
            "txn_id": "transaction_id",
            "trade_date": "trade_date",
            "name": "trader",
        },
        "normalization_rules": {"uppercase_strings": True, "date_format": "%Y-%m-%d"},
    }

    out = normalize_dataset(df, config)
    assert "transaction_id" in out.columns
    assert out.loc[0, "trader"] == "ALICE"
    assert out.loc[0, "trade_date"] == "2025-01-01"
