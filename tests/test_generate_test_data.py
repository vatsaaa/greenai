import pandas as pd
from scripts.generate_test_data import generate_base_dataset, create_source_datasets


def test_generate_base_dataset_length_and_columns():
    df = generate_base_dataset(10)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 10
    assert "transaction_id" in df.columns


def test_create_source_datasets_noise():
    truth = generate_base_dataset(50)
    a, b = create_source_datasets(truth)
    # Expect both to be DataFrames and not empty
    assert isinstance(a, pd.DataFrame)
    assert isinstance(b, pd.DataFrame)
    assert len(a) > 0 and len(b) > 0
