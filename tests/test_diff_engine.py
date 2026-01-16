from types import SimpleNamespace
from backend import diff_engine


def test_is_numeric():
    assert diff_engine.is_numeric("123")
    assert diff_engine.is_numeric(12.3)
    assert not diff_engine.is_numeric("abc")


def test_compare_values_numeric_within_tolerance():
    # values within tolerance => no diff
    assert diff_engine.compare_values("amt", "100.00", "100.002") is None


def test_compare_values_numeric_outside_tolerance():
    res = diff_engine.compare_values("amt", "100.00", "100.1")
    assert res is not None
    assert res["type"] == "NUMERIC_MISMATCH"


def test_compare_values_nulls():
    res = diff_engine.compare_values("f", None, "abc")
    assert res and res["type"] == "NULL_MISMATCH"


def test_process_record_missing_source_a():
    rec = SimpleNamespace(
        source_a_ref_id=None,
        source_b_ref_id="b",
        normalized_data_a={},
        normalized_data_b={},
    )
    diffs = diff_engine.process_record(rec)
    assert len(diffs) == 1
    assert diffs[0]["diff_type"] == "MISSING_IN_SOURCE_A"


def test_process_record_field_diff():
    rec = SimpleNamespace(
        source_a_ref_id="a",
        source_b_ref_id="b",
        normalized_data_a={"amount": "100.00", "name": "Alice"},
        normalized_data_b={"amount": "100.50", "name": "Alicia"},
    )
    diffs = diff_engine.process_record(rec)
    assert any(d["field_name"] == "amount" for d in diffs)
    assert any(d["field_name"] == "name" for d in diffs)
