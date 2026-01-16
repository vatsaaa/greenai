"""
This script generates synthetic test data for a data reconciliation system.
It creates two source datasets (Source A and Source B) from a 'Ground Truth' dataset,
"""

import pandas as pd
import numpy as np
from faker import Faker
import uuid
import random
import os
from datetime import timedelta
from typing import Tuple

# Configuration
OUTPUT_DIR: str = "./data_ingest"
NUM_RECORDS: int = 1000
RANDOM_SEED: int = 42

# Initialize Faker
fake = Faker()
Faker.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


def generate_base_dataset(n: int) -> pd.DataFrame:
    """
    Generates a 'Ground Truth' dataset representing the actual transactions
    that occurred before system fragmentation.
    """
    data = []
    currencies = ["USD", "EUR", "GBP", "JPY", "CAD"]

    print(f"Generating {n} base records...")

    for _ in range(n):
        txn_date = fake.date_between(start_date="-30d", end_date="today")

        record = {
            "transaction_id": str(uuid.uuid4()),
            "trade_date": txn_date,
            "settlement_date": txn_date + timedelta(days=2),
            "counterparty": fake.company(),
            "buy_sell": random.choice(["BUY", "SELL"]),
            "currency": random.choice(currencies),
            "amount": round(random.uniform(1000.00, 1000000.00), 2),
            "trader_id": fake.bothify(text="TRADER-###"),
        }
        data.append(record)

    return pd.DataFrame(data)


def create_source_datasets(df_truth: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Splits the truth dataset into Source A and Source B and introduces noise
    to simulate real-world reconciliation scenarios.
    """
    print("Splitting datasets and introducing noise...")

    # 1. SCENARIO: Missing Records (The "Left Join" vs "Inner Join" problem)
    # Source A has 95% of the data, Source B has 95% of the data.
    # This creates ~90% overlap, and 5% unique to A, 5% unique to B.
    mask_a = np.random.rand(len(df_truth)) < 0.95
    mask_b = np.random.rand(len(df_truth)) < 0.95

    df_a = df_truth[mask_a].copy()
    df_b = df_truth[mask_b].copy()

    # 2. SCENARIO: Noise Injection into Source B (simulating System B idiosyncrasies)

    # A. FX/Rounding Variance (Simulating 'ROUNDING_DIFF' or 'FX_VARIANCE')
    # Affects 10% of records in B
    # We alter the amount by a tiny fraction (e.g., +/- 0.005 to 0.01)
    rows_to_perturb_amt = df_b.sample(frac=0.10).index
    df_b.loc[rows_to_perturb_amt, "amount"] = df_b.loc[
        rows_to_perturb_amt, "amount"
    ] * np.random.uniform(0.9999, 1.0001, size=len(rows_to_perturb_amt))
    # Round to 2 decimals to simulate "hard" values
    df_b.loc[rows_to_perturb_amt, "amount"] = df_b.loc[
        rows_to_perturb_amt, "amount"
    ].round(2)

    # B. Data Entry Errors / Typos (Simulating 'MANUAL_ENTRY_ERR')
    # Affects 2% of records in B (Counterparty name changes)
    rows_to_typo = df_b.sample(frac=0.02).index
    df_b.loc[rows_to_typo, "counterparty"] = df_b.loc[
        rows_to_typo, "counterparty"
    ].apply(lambda x: x + " Inc" if "Inc" not in x else x.replace("Inc", "Ltd"))

    # C. Date Mismatches (Simulating 'TIMING_LAG')
    # Affects 5% of records in B (Trade date shifts by 1 day)
    rows_to_shift_date = df_b.sample(frac=0.05).index
    # We cast to datetime to allow arithmetic, then formatting back might be needed depending on CSV requirements
    # Here we assume pandas handles the object type gracefully or we convert
    df_b["trade_date"] = pd.to_datetime(df_b["trade_date"])
    df_b.loc[rows_to_shift_date, "trade_date"] = df_b.loc[
        rows_to_shift_date, "trade_date"
    ] + timedelta(days=1)

    # 3. SCENARIO: Format Differences (Metadata mismatch)
    # Source A uses 'BUY/SELL'. Source B uses 'B/S'.
    df_b["buy_sell"] = df_b["buy_sell"].map({"BUY": "B", "SELL": "S"})

    return df_a, df_b


def save_datasets(df_a: pd.DataFrame, df_b: pd.DataFrame, output_dir: str) -> None:
    """Saves the dataframes to CSV."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    path_a = os.path.join(output_dir, "source_system_a.csv")
    path_b = os.path.join(output_dir, "source_system_b.csv")

    # Ensure dates are string formatted for CSV consistency
    df_a.to_csv(path_a, index=False, date_format="%Y-%m-%d")
    df_b.to_csv(path_b, index=False, date_format="%Y-%m-%d")

    print("\nSUCCESS: Data generation complete.")
    print(f"Source A: {len(df_a)} records -> {path_a}")
    print(f"Source B: {len(df_b)} records -> {path_b}")


if __name__ == "__main__":
    # Ensure dependencies are installed: pip install pandas numpy faker

    truth_df = generate_base_dataset(NUM_RECORDS)
    source_a, source_b = create_source_datasets(truth_df)
    save_datasets(source_a, source_b, OUTPUT_DIR)
