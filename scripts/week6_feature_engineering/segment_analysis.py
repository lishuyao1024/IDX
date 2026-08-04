"""Week 6 segmented market analysis for engineered residential sold data.

The script creates summaries for the four selected handbook dimensions:

1. PropertySubType
2. CountyOrParish
3. ListOfficeName
4. BuyerOfficeName

PropertyType is excluded because the Week 1 Residential filter leaves only one
value. MLSAreaMajor is excluded from the current scope because of its high
cardinality and material missing/undefined share.

Duplicate ListingKey values are resolved by keeping the last occurrence. The
monthly source files were concatenated in chronological order, so this selects
the most recently loaded snapshot and prevents duplicate transaction counts and
sales volume. Negative transaction-duration values are retained in the source
data but excluded from duration averages.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "week6_feature_engineering"
INPUT_FILE = (
    OUTPUT_DIR / "CRMLSSold_Residential_202401_202606_Week6_Engineered.csv"
)

OUTPUT_FILES = {
    "PropertySubType": OUTPUT_DIR / "week6_summary_by_property_subtype.csv",
    "CountyOrParish": OUTPUT_DIR / "week6_summary_by_county.csv",
    "ListOfficeName": OUTPUT_DIR / "week6_summary_by_list_office.csv",
    "BuyerOfficeName": OUTPUT_DIR / "week6_summary_by_buyer_office.csv",
}

TOP_100_FILES = {
    "ListOfficeName": OUTPUT_DIR / "week6_top100_list_offices.csv",
    "BuyerOfficeName": OUTPUT_DIR / "week6_top100_buyer_offices.csv",
}

SEGMENT_COLUMNS = list(OUTPUT_FILES)
SOURCE_COLUMNS = [
    "ListingKey",
    "ClosePrice",
    "PropertySubType",
    "CountyOrParish",
    "ListOfficeName",
    "BuyerOfficeName",
    "price_per_sqft",
    "days_on_market",
    "price_ratio",
    "close_to_original_list_ratio",
    "listing_to_contract_days",
    "contract_to_close_days",
    "negative_listing_to_contract_flag",
    "negative_contract_to_close_flag",
]

MISSING_LABEL = "Missing/Unknown"
OFFICE_PLACEHOLDERS = {
    "",
    "-",
    "MISSING/UNKNOWN",
    "N/A",
    "NA",
    "NONE",
    "NULL",
    "UNKNOWN",
}


def validate_input() -> None:
    """Confirm the engineered input exists and contains required fields."""
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Engineered Week 6 input not found: {INPUT_FILE}")

    columns = pd.read_csv(INPUT_FILE, nrows=0).columns.tolist()
    missing = sorted(set(SOURCE_COLUMNS).difference(columns))
    if missing:
        raise ValueError("Missing required input columns: " + ", ".join(missing))


def clean_label(series: pd.Series) -> pd.Series:
    """Trim segment labels and retain missing values as an explicit group."""
    cleaned = series.astype("string").str.strip()
    cleaned = cleaned.mask(cleaned.eq(""))
    return cleaned.fillna(MISSING_LABEL)


def load_analysis_data() -> tuple[pd.DataFrame, int, int]:
    """Load required fields, deduplicate transactions, and prepare measures."""
    data = pd.read_csv(INPUT_FILE, usecols=SOURCE_COLUMNS, low_memory=False)
    source_rows = len(data)

    if data["ListingKey"].isna().any():
        raise ValueError("ListingKey contains missing values; cannot deduplicate safely.")

    # Week 1 appended monthly files from oldest to newest. Keeping the last
    # occurrence selects the newest available snapshot for repeated keys.
    data = data.drop_duplicates(subset="ListingKey", keep="last").copy()
    unique_transaction_rows = len(data)

    numeric_columns = [
        "ClosePrice",
        "price_per_sqft",
        "days_on_market",
        "price_ratio",
        "close_to_original_list_ratio",
        "listing_to_contract_days",
        "contract_to_close_days",
    ]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    for column in SEGMENT_COLUMNS:
        data[column] = clean_label(data[column])

    listing_negative = data["negative_listing_to_contract_flag"].astype(bool)
    closing_negative = data["negative_contract_to_close_flag"].astype(bool)

    data["listing_to_contract_days_valid"] = data[
        "listing_to_contract_days"
    ].mask(listing_negative | data["listing_to_contract_days"].lt(0))
    data["contract_to_close_days_valid"] = data[
        "contract_to_close_days"
    ].mask(closing_negative | data["contract_to_close_days"].lt(0))

    return data, source_rows, unique_transaction_rows


def create_segment_summary(
    data: pd.DataFrame,
    group_column: str,
) -> pd.DataFrame:
    """Create one consistent market summary for a selected segment field."""
    summary = (
        data.groupby(group_column, dropna=False)
        .agg(
            transaction_count=("ListingKey", "nunique"),
            total_sales_volume=("ClosePrice", "sum"),
            median_close_price=("ClosePrice", "median"),
            median_price_per_sqft=("price_per_sqft", "median"),
            average_days_on_market=("days_on_market", "mean"),
            median_days_on_market=("days_on_market", "median"),
            average_price_ratio=("price_ratio", "mean"),
            average_original_price_ratio=(
                "close_to_original_list_ratio",
                "mean",
            ),
            average_listing_to_contract_days=(
                "listing_to_contract_days_valid",
                "mean",
            ),
            average_contract_to_close_days=(
                "contract_to_close_days_valid",
                "mean",
            ),
        )
        .reset_index()
    )

    total_transactions = summary["transaction_count"].sum()
    total_sales_volume = summary["total_sales_volume"].sum()
    summary["transaction_share_pct"] = (
        summary["transaction_count"] / total_transactions * 100
    )
    summary["sales_volume_share_pct"] = (
        summary["total_sales_volume"] / total_sales_volume * 100
    )

    summary["transaction_count_rank"] = (
        summary["transaction_count"]
        .rank(method="min", ascending=False)
        .astype("int64")
    )
    summary["sales_volume_rank"] = (
        summary["total_sales_volume"]
        .rank(method="min", ascending=False)
        .astype("int64")
    )

    currency_columns = [
        "total_sales_volume",
        "median_close_price",
        "median_price_per_sqft",
    ]
    day_columns = [
        "average_days_on_market",
        "median_days_on_market",
        "average_listing_to_contract_days",
        "average_contract_to_close_days",
    ]
    ratio_columns = [
        "average_price_ratio",
        "average_original_price_ratio",
    ]
    share_columns = ["transaction_share_pct", "sales_volume_share_pct"]

    summary[currency_columns] = summary[currency_columns].round(2)
    summary[day_columns] = summary[day_columns].round(2)
    summary[ratio_columns] = summary[ratio_columns].round(4)
    # Office summaries contain tens of thousands of groups. Eight decimal
    # places prevent row-level rounding from materially moving the displayed
    # total away from 100% when shares are summed across the full table.
    summary[share_columns] = summary[share_columns].round(8)

    return summary.sort_values(
        ["total_sales_volume", "transaction_count"],
        ascending=[False, False],
    ).reset_index(drop=True)


def rankable_office_mask(series: pd.Series) -> pd.Series:
    """Exclude missing, placeholder, and nonmember labels from Top 100 tables."""
    normalized = series.astype("string").str.strip().str.upper()
    placeholder = normalized.isin(OFFICE_PLACEHOLDERS)
    nonmember = normalized.str.contains(
        r"NON\s*MEMBER|NONMEMBER",
        regex=True,
        na=False,
    )
    return ~(placeholder | nonmember)


def main() -> None:
    validate_input()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data, source_rows, unique_transaction_rows = load_analysis_data()

    summaries: dict[str, pd.DataFrame] = {}
    for segment in SEGMENT_COLUMNS:
        summary = create_segment_summary(data, segment)
        summary.to_csv(OUTPUT_FILES[segment], index=False)
        summaries[segment] = summary
        print(
            f"{segment}: {len(summary):,} groups -> {OUTPUT_FILES[segment].name}"
        )

    for office_column, output_path in TOP_100_FILES.items():
        office_summary = summaries[office_column]
        top_100 = (
            office_summary.loc[
                rankable_office_mask(office_summary[office_column])
            ]
            .sort_values(
                ["total_sales_volume", "transaction_count"],
                ascending=[False, False],
            )
            .head(100)
            .reset_index(drop=True)
        )
        top_100.insert(0, "top100_sales_volume_position", range(1, len(top_100) + 1))
        top_100.to_csv(output_path, index=False)
        print(f"{office_column} Top 100 -> {output_path.name}")

    duplicate_rows_removed = source_rows - unique_transaction_rows
    print(f"Source rows: {source_rows:,}")
    print(f"Unique transactions analyzed: {unique_transaction_rows:,}")
    print(f"Duplicate transaction rows excluded: {duplicate_rows_removed:,}")
    print("Week 6 segment analysis completed successfully.")


if __name__ == "__main__":
    main()
