"""Week 5 MLS quality flags, column review, and cleaned dataset exports.

Inputs are the Week 4 initially prepared Sold and Listing CSVs. This script:

1. reviews columns above 90% missing and exact redundant columns;
2. creates handbook-required numeric, date, and geographic quality flags;
3. removes only records that fail explicit numeric rules or required-field rules;
4. retains date/geographic issues with flags for transparent downstream filtering;
5. exports two cleaned CSVs and auditable validation/removal summaries.

Statistical outlier filtering is intentionally excluded because the handbook
assigns IQR-based outlier handling to Week 7.
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "week4_5_data_cleaning"

INPUT_FILES = {
    "sold": OUTPUT_DIR
    / "CRMLSSold_Residential_202401_202606_Initially_Prepared.csv",
    "listing": OUTPUT_DIR
    / "CRMLSListing_Residential_202401_202606_Initially_Prepared.csv",
}

CLEANED_FILES = {
    "sold": OUTPUT_DIR / "CRMLSSold_Residential_202401_202606_Week5_Cleaned.csv",
    "listing": OUTPUT_DIR
    / "CRMLSListing_Residential_202401_202606_Week5_Cleaned.csv",
}

MISSING_SUMMARY_PATH = OUTPUT_DIR / "missing_value_summary.csv"
CHUNK_SIZE = 50_000
HIGH_MISSING_THRESHOLD_PCT = 90.0

DATE_COLUMNS = [
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
    "ContractStatusChangeDate",
]

NUMERIC_COLUMNS = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "DaysOnMarket",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "YearBuilt",
    "Latitude",
    "Longitude",
    "rate_30yr_fixed",
]

INVALID_NUMERIC_RULES = {
    "invalid_close_price_flag": ("ClosePrice", "le", 0),
    "invalid_living_area_flag": ("LivingArea", "le", 0),
    "negative_days_on_market_flag": ("DaysOnMarket", "lt", 0),
    "negative_bedrooms_flag": ("BedroomsTotal", "lt", 0),
    "negative_bathrooms_flag": ("BathroomsTotalInteger", "lt", 0),
}

REQUIRED_FIELDS = {
    # A Sold record without these fields cannot support core closed-sale
    # analysis. Other partial fields remain available for applicable analyses.
    "sold": ["ListingKey", "CloseDate", "ClosePrice"],
    # Listing rows can legitimately lack close fields, but require an ID,
    # listing date, and list price for listing-market analysis.
    "listing": ["ListingKey", "ListingContractDate", "ListPrice"],
}

# Core fields are retained even if a future extract crosses the high-missing
# threshold. This prevents an automatic completeness rule from deleting fields
# that are essential for a specific downstream analysis.
PROTECTED_CORE_COLUMNS = {
    "ListingKey",
    "ListingId",
    "PropertyType",
    "PropertySubType",
    "MlsStatus",
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
    "ContractStatusChangeDate",
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "DaysOnMarket",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "YearBuilt",
    "Latitude",
    "Longitude",
    "StateOrProvince",
    "CountyOrParish",
    "City",
    "PostalCode",
    "MLSAreaMajor",
    "ListOfficeName",
    "BuyerOfficeName",
    "ListAgentFullName",
    "BuyerAgentMlsId",
    "year_month",
    "rate_30yr_fixed",
}

FLAG_COLUMNS = [
    # Numeric validity
    "invalid_close_price_flag",
    "invalid_living_area_flag",
    "negative_days_on_market_flag",
    "negative_bedrooms_flag",
    "negative_bathrooms_flag",
    "invalid_numeric_flag",
    "missing_required_field_flag",
    "remove_from_cleaned_flag",
    # Date consistency
    "listing_after_close_flag",
    "purchase_after_close_flag",
    "negative_timeline_flag",
    # Geographic quality
    "missing_coordinates_flag",
    "zero_coordinates_flag",
    "positive_longitude_flag",
    "out_of_state_flag",
    "implausible_coordinates_flag",
    "outside_california_bounds_flag",
    "geographic_review_flag",
]

FLAG_METADATA = {
    "invalid_close_price_flag": (
        "numeric",
        "ClosePrice <= 0",
        "remove",
    ),
    "invalid_living_area_flag": (
        "numeric",
        "LivingArea <= 0",
        "remove",
    ),
    "negative_days_on_market_flag": (
        "numeric",
        "DaysOnMarket < 0",
        "remove",
    ),
    "negative_bedrooms_flag": (
        "numeric",
        "BedroomsTotal < 0",
        "remove",
    ),
    "negative_bathrooms_flag": (
        "numeric",
        "BathroomsTotalInteger < 0",
        "remove",
    ),
    "invalid_numeric_flag": (
        "numeric",
        "Any explicit invalid-numeric rule is true",
        "remove",
    ),
    "missing_required_field_flag": (
        "completeness",
        "A dataset-specific required field is missing",
        "remove",
    ),
    "remove_from_cleaned_flag": (
        "removal",
        "Invalid numeric value or missing required field",
        "remove",
    ),
    "listing_after_close_flag": (
        "date",
        "ListingContractDate > CloseDate",
        "retain_and_flag",
    ),
    "purchase_after_close_flag": (
        "date",
        "PurchaseContractDate > CloseDate",
        "retain_and_flag",
    ),
    "negative_timeline_flag": (
        "date",
        "Any transaction date is earlier than its logical predecessor",
        "retain_and_flag",
    ),
    "missing_coordinates_flag": (
        "geographic",
        "Latitude or Longitude is missing",
        "retain_and_flag",
    ),
    "zero_coordinates_flag": (
        "geographic",
        "Latitude = 0 or Longitude = 0",
        "retain_and_flag",
    ),
    "positive_longitude_flag": (
        "geographic",
        "Longitude > 0",
        "retain_and_flag",
    ),
    "out_of_state_flag": (
        "geographic",
        "StateOrProvince is populated but is not CA/California",
        "retain_and_flag",
    ),
    "implausible_coordinates_flag": (
        "geographic",
        "Latitude is outside [-90, 90] or Longitude outside [-180, 180]",
        "retain_and_flag",
    ),
    "outside_california_bounds_flag": (
        "geographic",
        "A CA record falls outside approximate CA coordinate bounds",
        "retain_and_flag",
    ),
    "geographic_review_flag": (
        "geographic",
        "Any geographic quality flag is true",
        "retain_and_flag",
    ),
}

REMOVAL_REASON_LABELS = {
    "invalid_close_price_flag": "ClosePrice <= 0",
    "invalid_living_area_flag": "LivingArea <= 0",
    "negative_days_on_market_flag": "DaysOnMarket < 0",
    "negative_bedrooms_flag": "BedroomsTotal < 0",
    "negative_bathrooms_flag": "BathroomsTotalInteger < 0",
    "missing_required_field_flag": "missing required field",
}


def write_csv_atomic(
    frame: pd.DataFrame,
    output_path: Path,
    mode: str,
    header: bool,
) -> None:
    """Append a chunk to a temporary output using stable CSV conventions."""

    frame.to_csv(
        output_path,
        mode=mode,
        header=header,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )


def verify_listing_key_redundancy(input_path: Path) -> tuple[bool, int, int]:
    """Verify ListingKeyNumeric is exactly equal to ListingKey in all rows."""

    header = pd.read_csv(input_path, nrows=0).columns
    if "ListingKey" not in header or "ListingKeyNumeric" not in header:
        return False, 0, 0

    compared_rows = 0
    mismatch_rows = 0
    for chunk in pd.read_csv(
        input_path,
        usecols=["ListingKey", "ListingKeyNumeric"],
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ):
        left = pd.to_numeric(chunk["ListingKey"], errors="coerce")
        right = pd.to_numeric(chunk["ListingKeyNumeric"], errors="coerce")
        equal = left.eq(right) | (left.isna() & right.isna())
        compared_rows += len(chunk)
        mismatch_rows += int((~equal).sum())

    return mismatch_rows == 0, compared_rows, mismatch_rows


def build_column_review(
    dataset: str,
    input_path: Path,
    missing_summary: pd.DataFrame,
) -> tuple[list[str], list[dict]]:
    """Choose auditable column drops and return a per-column review table."""

    columns = pd.read_csv(input_path, nrows=0).columns.tolist()
    dataset_missing = (
        missing_summary.loc[missing_summary["dataset"].eq(dataset)]
        .set_index("column")
        .reindex(columns)
    )

    redundant_equal, compared_rows, mismatch_rows = verify_listing_key_redundancy(
        input_path
    )
    redundant_map = (
        {"ListingKeyNumeric": "ListingKey"} if redundant_equal else {}
    )

    drop_columns: list[str] = []
    review_rows: list[dict] = []
    for column in columns:
        missing_pct_value = dataset_missing.loc[column, "missing_pct"]
        missing_count_value = dataset_missing.loc[column, "missing_count"]
        missing_pct = (
            float(missing_pct_value) if pd.notna(missing_pct_value) else float("nan")
        )
        missing_count = (
            int(missing_count_value) if pd.notna(missing_count_value) else pd.NA
        )
        high_missing = pd.notna(missing_pct) and (
            missing_pct > HIGH_MISSING_THRESHOLD_PCT
        )
        protected = column in PROTECTED_CORE_COLUMNS
        redundant_of = redundant_map.get(column, "")

        if redundant_of:
            action = "drop_exact_redundant"
            reason = (
                f"Exactly equals {redundant_of} across {compared_rows:,} rows; "
                f"{mismatch_rows} mismatches"
            )
            drop_columns.append(column)
        elif high_missing and not protected:
            action = "drop_high_missing"
            reason = (
                f"Missing rate {missing_pct:.6f}% exceeds "
                f"{HIGH_MISSING_THRESHOLD_PCT:.0f}% and column is not protected"
            )
            drop_columns.append(column)
        elif high_missing and protected:
            action = "retain_protected_core"
            reason = "High missingness, but retained as a protected core field"
        else:
            action = "retain"
            reason = "Does not meet an approved drop rule"

        review_rows.append(
            {
                "dataset": dataset,
                "column": column,
                "missing_count_before_cleaning": missing_count,
                "missing_pct_before_cleaning": missing_pct,
                "high_missing_gt_90_pct": high_missing,
                "protected_core_column": protected,
                "exact_redundant_of": redundant_of,
                "review_action": action,
                "review_reason": reason,
            }
        )

    return drop_columns, review_rows


def ensure_types(chunk: pd.DataFrame) -> pd.DataFrame:
    """Restore date/numeric types because CSV files do not retain dtype metadata."""

    for column in DATE_COLUMNS:
        if column in chunk.columns:
            chunk[column] = pd.to_datetime(chunk[column], errors="coerce")
    for column in NUMERIC_COLUMNS:
        if column in chunk.columns:
            chunk[column] = pd.to_numeric(chunk[column], errors="coerce")
    return chunk


def numeric_rule_mask(
    series: pd.Series,
    operator: str,
    threshold: float,
) -> pd.Series:
    """Evaluate a numeric business rule while treating missing values separately."""

    if operator == "le":
        result = series.le(threshold)
    elif operator == "lt":
        result = series.lt(threshold)
    else:
        raise ValueError(f"Unsupported numeric-rule operator: {operator}")
    return (series.notna() & result).fillna(False)


def add_numeric_flags(chunk: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """Create invalid-value and required-field flags."""

    for flag, (column, operator, threshold) in INVALID_NUMERIC_RULES.items():
        if column in chunk.columns:
            chunk[flag] = numeric_rule_mask(chunk[column], operator, threshold)
        else:
            chunk[flag] = False

    numeric_flags = list(INVALID_NUMERIC_RULES)
    chunk["invalid_numeric_flag"] = chunk[numeric_flags].any(axis=1)

    required_columns = [
        column for column in REQUIRED_FIELDS[dataset] if column in chunk.columns
    ]
    missing_declared_columns = [
        column for column in REQUIRED_FIELDS[dataset] if column not in chunk.columns
    ]
    if missing_declared_columns:
        raise ValueError(
            f"{dataset} is missing required columns: {missing_declared_columns}"
        )
    chunk["missing_required_field_flag"] = chunk[required_columns].isna().any(axis=1)
    chunk["remove_from_cleaned_flag"] = (
        chunk["invalid_numeric_flag"] | chunk["missing_required_field_flag"]
    )
    return chunk


def add_date_flags(chunk: pd.DataFrame) -> pd.DataFrame:
    """Create the handbook date-consistency flags."""

    listing = chunk["ListingContractDate"]
    purchase = chunk["PurchaseContractDate"]
    close = chunk["CloseDate"]

    chunk["listing_after_close_flag"] = (
        listing.notna() & close.notna() & listing.gt(close)
    )
    chunk["purchase_after_close_flag"] = (
        purchase.notna() & close.notna() & purchase.gt(close)
    )

    purchase_before_listing = (
        purchase.notna() & listing.notna() & purchase.lt(listing)
    )
    close_before_purchase = close.notna() & purchase.notna() & close.lt(purchase)
    close_before_listing = close.notna() & listing.notna() & close.lt(listing)
    chunk["negative_timeline_flag"] = (
        purchase_before_listing | close_before_purchase | close_before_listing
    )
    return chunk


def add_geographic_flags(chunk: pd.DataFrame) -> pd.DataFrame:
    """Create missing, sentinel, sign, state, and plausibility coordinate flags."""

    latitude = chunk["Latitude"]
    longitude = chunk["Longitude"]
    coordinates_present = latitude.notna() & longitude.notna()

    chunk["missing_coordinates_flag"] = ~coordinates_present
    chunk["zero_coordinates_flag"] = coordinates_present & (
        latitude.eq(0) | longitude.eq(0)
    )
    chunk["positive_longitude_flag"] = longitude.notna() & longitude.gt(0)

    state = chunk["StateOrProvince"].astype("string").str.strip().str.upper()
    california_state = state.isin(["CA", "CALIFORNIA"])
    chunk["out_of_state_flag"] = state.notna() & ~california_state

    chunk["implausible_coordinates_flag"] = coordinates_present & (
        ~latitude.between(-90, 90) | ~longitude.between(-180, 180)
    )

    # Approximate California bounds used only as a review flag, not a deletion
    # rule. Out-of-state records are handled by their own flag.
    chunk["outside_california_bounds_flag"] = (
        coordinates_present
        & california_state
        & (
            ~latitude.between(32.0, 42.1)
            | ~longitude.between(-124.5, -114.0)
        )
    )

    geographic_components = [
        "missing_coordinates_flag",
        "zero_coordinates_flag",
        "positive_longitude_flag",
        "out_of_state_flag",
        "implausible_coordinates_flag",
        "outside_california_bounds_flag",
    ]
    chunk["geographic_review_flag"] = chunk[geographic_components].any(axis=1)
    return chunk


def build_removal_reason(chunk: pd.DataFrame) -> pd.Series:
    """Combine all applicable removal causes into a readable audit string."""

    reasons = pd.Series("", index=chunk.index, dtype="string")
    for flag, label in REMOVAL_REASON_LABELS.items():
        separator = reasons.ne("").map({True: "; ", False: ""})
        reasons = reasons.mask(chunk[flag], reasons + separator + label)
    return reasons


def update_flag_counts(
    counts: dict[str, int],
    chunk: pd.DataFrame,
) -> None:
    """Accumulate true counts for every quality flag."""

    for flag in FLAG_COLUMNS:
        counts[flag] += int(chunk[flag].sum())


def process_dataset(
    dataset: str,
    input_path: Path,
    output_path: Path,
    drop_columns: list[str],
    removed_audit_path: Path,
    removed_audit_header_written: bool,
) -> tuple[dict, list[dict], Counter, bool]:
    """Flag, filter, and export one cleaned dataset in chunks."""

    temporary_output = output_path.with_suffix(output_path.suffix + ".tmp")
    if temporary_output.exists():
        temporary_output.unlink()

    input_rows = 0
    output_rows = 0
    input_columns = len(pd.read_csv(input_path, nrows=0).columns)
    output_columns = None
    flag_counts: dict[str, int] = defaultdict(int)
    removal_reason_counts: Counter = Counter()
    listing_key_counts: Counter = Counter()
    cleaned_missing_counts: dict[str, int] = defaultdict(int)
    cleaned_dtype_sets: dict[str, set[str]] = defaultdict(set)
    chunk_number = 0

    try:
        for chunk in pd.read_csv(
            input_path,
            chunksize=CHUNK_SIZE,
            low_memory=False,
        ):
            chunk_number += 1
            input_rows += len(chunk)
            chunk = ensure_types(chunk)
            chunk = add_numeric_flags(chunk, dataset)
            chunk = add_date_flags(chunk)
            chunk = add_geographic_flags(chunk)
            chunk["removal_reason"] = build_removal_reason(chunk)
            update_flag_counts(flag_counts, chunk)

            if "ListingKey" in chunk.columns:
                listing_key_counts.update(
                    chunk["ListingKey"].dropna().astype("string").tolist()
                )

            removed = chunk.loc[chunk["remove_from_cleaned_flag"]].copy()
            if not removed.empty:
                removal_reason_counts.update(removed["removal_reason"].tolist())
                audit_columns = [
                    "ListingKey",
                    "ListingId",
                    "ClosePrice",
                    "LivingArea",
                    "DaysOnMarket",
                    "BedroomsTotal",
                    "BathroomsTotalInteger",
                    *list(INVALID_NUMERIC_RULES),
                    "missing_required_field_flag",
                    "removal_reason",
                ]
                available_audit_columns = [
                    column for column in audit_columns if column in removed.columns
                ]
                removed.insert(0, "dataset", dataset)
                write_csv_atomic(
                    removed[["dataset", *available_audit_columns]],
                    removed_audit_path,
                    mode="a",
                    header=not removed_audit_header_written,
                )
                removed_audit_header_written = True

            cleaned = chunk.loc[~chunk["remove_from_cleaned_flag"]].copy()
            cleaned.drop(columns=drop_columns, inplace=True, errors="ignore")
            cleaned.drop(columns=["removal_reason"], inplace=True)
            output_rows += len(cleaned)

            if output_columns is None:
                output_columns = len(cleaned.columns)
            elif output_columns != len(cleaned.columns):
                raise ValueError(f"{dataset} output column count changed across chunks")

            for column in cleaned.columns:
                cleaned_missing_counts[column] += int(cleaned[column].isna().sum())
                cleaned_dtype_sets[column].add(str(cleaned[column].dtype))

            write_csv_atomic(
                cleaned,
                temporary_output,
                mode="w" if chunk_number == 1 else "a",
                header=chunk_number == 1,
            )

        os.replace(temporary_output, output_path)
    except Exception:
        if temporary_output.exists():
            temporary_output.unlink()
        raise

    duplicate_key_affected_rows = sum(
        count for count in listing_key_counts.values() if count > 1
    )
    duplicate_key_values = sum(
        1 for count in listing_key_counts.values() if count > 1
    )

    dataset_summary = {
        "dataset": dataset,
        "input_file": str(input_path.relative_to(PROJECT_ROOT)),
        "cleaned_output_file": str(output_path.relative_to(PROJECT_ROOT)),
        "input_rows": input_rows,
        "removed_rows": input_rows - output_rows,
        "removed_pct": round(
            ((input_rows - output_rows) / input_rows * 100), 6
        )
        if input_rows
        else 0.0,
        "cleaned_rows": output_rows,
        "input_columns": input_columns,
        "dropped_columns": len(drop_columns),
        "added_flag_columns": len(FLAG_COLUMNS),
        "cleaned_columns": output_columns,
        "listing_key_duplicate_values_retained": duplicate_key_values,
        "rows_affected_by_duplicate_listing_keys_retained": (
            duplicate_key_affected_rows
        ),
        "duplicate_key_action": (
            "retained_and_reported; monthly aggregation may contain repeated keys"
        ),
    }

    flag_summary_rows = []
    for flag in FLAG_COLUMNS:
        category, rule, action = FLAG_METADATA[flag]
        count = flag_counts[flag]
        flag_summary_rows.append(
            {
                "dataset": dataset,
                "category": category,
                "flag": flag,
                "rule": rule,
                "true_count_before_filtering": count,
                "true_pct_before_filtering": round(count / input_rows * 100, 6)
                if input_rows
                else 0.0,
                "action": action,
            }
        )

    cleaned_missing_rows = [
        {
            "dataset": dataset,
            "column": column,
            "cleaned_dtype_in_memory": " | ".join(
                sorted(cleaned_dtype_sets[column])
            ),
            "cleaned_row_count": output_rows,
            "missing_count": cleaned_missing_counts[column],
            "missing_pct": round(
                cleaned_missing_counts[column] / output_rows * 100, 6
            )
            if output_rows
            else 0.0,
        }
        for column in pd.read_csv(output_path, nrows=0).columns
    ]

    return (
        dataset_summary,
        flag_summary_rows,
        removal_reason_counts,
        removed_audit_header_written,
        cleaned_missing_rows,
    )


def write_summary(filename: str, rows: list[dict]) -> None:
    """Write one audit summary in an Excel-compatible encoding."""

    pd.DataFrame(rows).to_csv(
        OUTPUT_DIR / filename,
        index=False,
        encoding="utf-8-sig",
    )


def main() -> None:
    for input_path in INPUT_FILES.values():
        if not input_path.exists():
            raise FileNotFoundError(f"Week 4 prepared input not found: {input_path}")
    if not MISSING_SUMMARY_PATH.exists():
        raise FileNotFoundError(
            f"Week 4 missing-value summary not found: {MISSING_SUMMARY_PATH}"
        )

    missing_summary = pd.read_csv(MISSING_SUMMARY_PATH)
    all_column_review_rows: list[dict] = []
    drop_columns_by_dataset: dict[str, list[str]] = {}

    for dataset, input_path in INPUT_FILES.items():
        drop_columns, review_rows = build_column_review(
            dataset,
            input_path,
            missing_summary,
        )
        drop_columns_by_dataset[dataset] = drop_columns
        all_column_review_rows.extend(review_rows)
        print(
            f"{dataset}: approved {len(drop_columns)} column drops "
            f"before row-level cleaning"
        )

    write_summary("week5_column_review_summary.csv", all_column_review_rows)

    removed_audit_path = OUTPUT_DIR / "week5_removed_records_audit.csv"
    if removed_audit_path.exists():
        removed_audit_path.unlink()
    removed_audit_header_written = False

    dataset_summaries: list[dict] = []
    flag_summaries: list[dict] = []
    removal_reason_rows: list[dict] = []
    cleaned_missing_rows: list[dict] = []

    for dataset, input_path in INPUT_FILES.items():
        print(f"Cleaning {dataset}: {input_path.name}")
        (
            dataset_summary,
            flag_summary_rows,
            removal_reason_counts,
            removed_audit_header_written,
            dataset_cleaned_missing_rows,
        ) = process_dataset(
            dataset,
            input_path,
            CLEANED_FILES[dataset],
            drop_columns_by_dataset[dataset],
            removed_audit_path,
            removed_audit_header_written,
        )
        dataset_summaries.append(dataset_summary)
        flag_summaries.extend(flag_summary_rows)
        cleaned_missing_rows.extend(dataset_cleaned_missing_rows)
        removal_reason_rows.extend(
            {
                "dataset": dataset,
                "removal_reason_combination": reason,
                "removed_rows": count,
            }
            for reason, count in sorted(removal_reason_counts.items())
        )
        print(
            f"  rows {dataset_summary['input_rows']:,} -> "
            f"{dataset_summary['cleaned_rows']:,}; "
            f"removed {dataset_summary['removed_rows']:,}"
        )

    write_summary("week5_cleaning_validation_summary.csv", dataset_summaries)
    write_summary("week5_quality_flag_summary.csv", flag_summaries)
    write_summary("week5_removal_reason_summary.csv", removal_reason_rows)
    write_summary("week5_cleaned_missing_value_summary.csv", cleaned_missing_rows)

    if not removed_audit_header_written:
        pd.DataFrame(
            columns=[
                "dataset",
                "ListingKey",
                "ListingId",
                "removal_reason",
            ]
        ).to_csv(
            removed_audit_path,
            index=False,
            encoding="utf-8-sig",
        )

    print("Week 5 quality flags and cleaned exports completed successfully.")


if __name__ == "__main__":
    main()
