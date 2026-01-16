import pandas as pd
from backend.attribution_engine import AttributionModel


def test_predict_missing_reasons():
    reason_map = {
        "MISSING_SOURCE_A": 1,
        "MISSING_SOURCE_B": 2,
        "ROUNDING_DIFF": 3,
        "FX_VARIANCE": 4,
        "MANUAL_ENTRY_ERR": 5,
        "UNKNOWN": 99,
    }

    model = AttributionModel(reason_map)

    # Missing in A
    row = pd.Series(
        {
            "diff_type": "MISSING_IN_SOURCE_A",
            "field_name": "ENTIRE_RECORD",
            "value_a": None,
            "value_b": "EXISTS",
        }
    )
    rid, conf = model.predict(row)
    assert rid == reason_map.get("MISSING_SOURCE_A")
    assert conf == 1.0

    # Numeric small delta -> rounding
    row = pd.Series(
        {
            "diff_type": "NUMERIC_MISMATCH",
            "field_name": "amount",
            "value_a": "100.00",
            "value_b": "100.01",
        }
    )
    rid, conf = model.predict(row)
    assert rid == reason_map.get("ROUNDING_DIFF")
    assert conf > 0.9

    # String minor punctuation change -> manual entry heuristic
    row = pd.Series(
        {
            "diff_type": "STRING_MISMATCH",
            "field_name": "counterparty",
            "value_a": "ACME, INC.",
            "value_b": "ACME INC",
        }
    )
    rid, conf = model.predict(row)
    assert rid == reason_map.get("MANUAL_ENTRY_ERR")
    assert conf >= 0.9
