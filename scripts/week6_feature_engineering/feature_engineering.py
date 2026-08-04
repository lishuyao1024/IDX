"""Week 6 feature engineering for the cleaned residential sold dataset.

This script creates the handbook-required market metrics without removing any
records. It reads the Week 5 cleaned sold CSV in chunks so the pipeline remains
practical on machines with limited memory, then exports:

1. the complete engineered sold dataset;
2. a 25-row sample with source fields and populated engineered metrics; and
3. a validation summary covering row counts, missing values, infinities, and
   negative values that need review.

The handbook repeats ClosePrice / OriginalListPrice for both "Price Ratio" and
"Close to Original List Ratio." For this project, price_ratio intentionally
uses ClosePrice / ListPrice, while close_to_original_list_ratio uses
ClosePrice / OriginalListPrice.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = (
    PROJECT_ROOT
    / "outputs"
    / "week4_5_data_cleaning"
    / "CRMLSSold_Residential_202401_202606_Week5_Cleaned.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "week6_feature_engineering"
ENGINEERED_FILE = (
    OUTPUT_DIR / "CRMLSSold_Residential_202401_202606_Week6_Engineered.csv"
)
SAMPLE_FILE = OUTPUT_DIR / "week6_engineered_sample.csv"
VALIDATION_FILE = OUTPUT_DIR / "week6_feature_engineering_validation.csv"

CHUNK_SIZE = 50_000
SAMPLE_SIZE = 25

REQUIRED_COLUMNS = [
    "ListingKey",
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "DaysOnMarket",
    "CloseDate",
    "ListingContractDate",
    "PurchaseContractDate",
]

DATE_COLUMNS = [
    "CloseDate",
    "ListingContractDate",
    "PurchaseContractDate",
]

ENGINEERED_COLUMNS = [
    "price_ratio",
    "close_to_original_list_ratio",
    "price_per_sqft",
    "days_on_market",
    "year",
    "month",
    "YrMo",
    "listing_to_contract_days",
    "contract_to_close_days",
]

FLAG_COLUMNS = [
    "negative_listing_to_contract_flag",
    "negative_contract_to_close_flag",
]

SAMPLE_COLUMNS = REQUIRED_COLUMNS + ENGINEERED_COLUMNS + FLAG_COLUMNS


def validate_input_schema() -> None:
    """Confirm that the input exists and contains every required source field."""
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Week 5 cleaned sold file not found: {INPUT_FILE}")

    input_columns = pd.read_csv(INPUT_FILE, nrows=0).columns.tolist()
    missing_columns = sorted(set(REQUIRED_COLUMNS).difference(input_columns))
    if missing_columns:
        raise ValueError(
            "Week 5 cleaned sold file is missing required columns: "
            + ", ".join(missing_columns)
        )


def safe_ratio(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    """Divide positive, non-null values and return NaN for invalid inputs."""
    numerator_numeric = pd.to_numeric(numerator, errors="coerce")
    denominator_numeric = pd.to_numeric(denominator, errors="coerce")
    valid = (
        numerator_numeric.notna()
        & denominator_numeric.notna()
        & numerator_numeric.gt(0)
        & denominator_numeric.gt(0)
    )

    result = pd.Series(np.nan, index=numerator.index, dtype="float64")
    result.loc[valid] = (
        numerator_numeric.loc[valid] / denominator_numeric.loc[valid]
    )
    return result


def engineer_features(chunk: pd.DataFrame) -> pd.DataFrame:
    """Create all Week 6 engineered metrics and date-quality review flags."""
    for column in DATE_COLUMNS:
        chunk[column] = pd.to_datetime(chunk[column], errors="coerce")

    chunk["price_ratio"] = safe_ratio(chunk["ClosePrice"], chunk["ListPrice"])
    chunk["close_to_original_list_ratio"] = safe_ratio(
        chunk["ClosePrice"], chunk["OriginalListPrice"]
    )
    chunk["price_per_sqft"] = safe_ratio(
        chunk["ClosePrice"], chunk["LivingArea"]
    )
    chunk["days_on_market"] = pd.to_numeric(
        chunk["DaysOnMarket"], errors="coerce"
    )

    chunk["year"] = chunk["CloseDate"].dt.year.astype("Int64")
    chunk["month"] = chunk["CloseDate"].dt.month.astype("Int64")
    chunk["YrMo"] = chunk["CloseDate"].dt.to_period("M").astype("string")

    chunk["listing_to_contract_days"] = (
        chunk["PurchaseContractDate"] - chunk["ListingContractDate"]
    ).dt.days.astype("Int64")
    chunk["contract_to_close_days"] = (
        chunk["CloseDate"] - chunk["PurchaseContractDate"]
    ).dt.days.astype("Int64")

    chunk["negative_listing_to_contract_flag"] = (
        chunk["listing_to_contract_days"].lt(0).fillna(False).astype(bool)
    )
    chunk["negative_contract_to_close_flag"] = (
        chunk["contract_to_close_days"].lt(0).fillna(False).astype(bool)
    )

    return chunk


def update_metric_totals(
    totals: dict[str, dict[str, float]],
    chunk: pd.DataFrame,
) -> None:
    """Accumulate deterministic validation statistics for each metric."""
    for column in ENGINEERED_COLUMNS:
        series = chunk[column]
        totals[column]["non_null_count"] += int(series.notna().sum())
        totals[column]["missing_count"] += int(series.isna().sum())

        if pd.api.types.is_numeric_dtype(series.dtype):
            numeric = pd.to_numeric(series, errors="coerce").astype("float64")
            totals[column]["infinite_count"] += int(np.isinf(numeric).sum())
            totals[column]["negative_count"] += int(numeric.lt(0).sum())


def build_validation_rows(
    totals: dict[str, dict[str, float]],
    input_rows: int,
    output_rows: int,
) -> list[dict[str, object]]:
    """Format pipeline- and metric-level checks as a single CSV table."""
    rows: list[dict[str, object]] = [
        {
            "check_type": "pipeline",
            "field": "row_count",
            "input_rows": input_rows,
            "output_rows": output_rows,
            "non_null_count": "",
            "missing_count": "",
            "infinite_count": "",
            "negative_count": "",
            "status": "PASS" if input_rows == output_rows else "FAIL",
        }
    ]

    for column in ENGINEERED_COLUMNS:
        metric = totals[column]
        rows.append(
            {
                "check_type": "engineered_metric",
                "field": column,
                "input_rows": input_rows,
                "output_rows": output_rows,
                "non_null_count": int(metric["non_null_count"]),
                "missing_count": int(metric["missing_count"]),
                "infinite_count": int(metric["infinite_count"]),
                "negative_count": int(metric["negative_count"]),
                "status": (
                    "PASS" if int(metric["infinite_count"]) == 0 else "FAIL"
                ),
            }
        )

    return rows


def main() -> None:
    validate_input_schema()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Opening the output on the first chunk with mode="w" makes reruns
    # deterministic and prevents accidental duplicate appends.
    input_rows = 0
    output_rows = 0
    sample_parts: list[pd.DataFrame] = []
    sample_rows_collected = 0
    metric_totals = {
        column: {
            "non_null_count": 0.0,
            "missing_count": 0.0,
            "infinite_count": 0.0,
            "negative_count": 0.0,
        }
        for column in ENGINEERED_COLUMNS
    }

    for chunk_number, chunk in enumerate(
        pd.read_csv(INPUT_FILE, chunksize=CHUNK_SIZE, low_memory=False),
        start=1,
    ):
        input_rows += len(chunk)
        chunk = engineer_features(chunk)
        output_rows += len(chunk)
        update_metric_totals(metric_totals, chunk)

        if sample_rows_collected < SAMPLE_SIZE:
            complete_sample_mask = chunk[ENGINEERED_COLUMNS].notna().all(axis=1)
            available = chunk.loc[complete_sample_mask, SAMPLE_COLUMNS]
            needed = SAMPLE_SIZE - sample_rows_collected
            selected = available.head(needed).copy()
            if not selected.empty:
                sample_parts.append(selected)
                sample_rows_collected += len(selected)

        chunk.to_csv(
            ENGINEERED_FILE,
            mode="w" if chunk_number == 1 else "a",
            header=chunk_number == 1,
            index=False,
            date_format="%Y-%m-%d",
        )
        print(
            f"Processed chunk {chunk_number}: {len(chunk):,} rows "
            f"({output_rows:,} total)"
        )

    if not sample_parts:
        raise ValueError(
            "No rows contain all engineered metrics; sample output cannot be created."
        )

    sample = pd.concat(sample_parts, ignore_index=True).head(SAMPLE_SIZE)
    sample.to_csv(SAMPLE_FILE, index=False, date_format="%Y-%m-%d")

    validation_rows = build_validation_rows(
        metric_totals,
        input_rows=input_rows,
        output_rows=output_rows,
    )
    validation = pd.DataFrame(validation_rows)
    validation.to_csv(VALIDATION_FILE, index=False)

    if input_rows != output_rows:
        raise AssertionError(
            f"Row count changed unexpectedly: {input_rows:,} -> {output_rows:,}"
        )

    failed_checks = validation.loc[validation["status"].eq("FAIL")]
    if not failed_checks.empty:
        raise AssertionError(
            "Week 6 validation failed:\n" + failed_checks.to_string(index=False)
        )

    print(f"Engineered dataset: {ENGINEERED_FILE}")
    print(f"Sample output: {SAMPLE_FILE}")
    print(f"Validation summary: {VALIDATION_FILE}")
    print(f"Rows preserved: {input_rows:,} -> {output_rows:,}")
    print("Week 6 feature engineering completed successfully.")


if __name__ == "__main__":
    main()
