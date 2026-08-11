"""Independent validation for the Week 7 outlier-detection deliverables."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
WEEK6_FILE = (
    BASE_DIR.parent
    / "week6_feature_engineering"
    / "CRMLSSold_Residential_202401_202606_Week6_Engineered.csv"
)
FLAGGED_FILE = (
    BASE_DIR / "CRMLSSold_Residential_202401_202606_Week7_Flagged.csv"
)
CLEAN_FILE = (
    BASE_DIR / "CRMLSSold_Residential_202401_202606_Week7_Clean_Filtered.csv"
)
SUMMARY_FILE = BASE_DIR / "week7_outlier_summary.csv"
COMPARISON_FILE = BASE_DIR / "week7_dataset_comparison.csv"
SAMPLE_FILE = BASE_DIR / "week7_flagged_sample.csv"
REPORT_FILE = BASE_DIR / "week7_before_after_comparison.md"

KEY_COLUMN = "ListingKey"
TARGET_COLUMNS = ["ClosePrice", "LivingArea", "DaysOnMarket"]
FLAG_PREFIXES = {
    "ClosePrice": "close_price",
    "LivingArea": "living_area",
    "DaysOnMarket": "days_on_market",
}


def assert_close(actual: float, expected: float, label: str) -> None:
    """Assert numeric equality at report-level precision."""
    if not np.isclose(actual, expected, rtol=1e-8, atol=1e-6, equal_nan=True):
        raise AssertionError(f"{label}: actual={actual}, expected={expected}")


def main() -> None:
    required_files = [
        WEEK6_FILE,
        FLAGGED_FILE,
        CLEAN_FILE,
        SUMMARY_FILE,
        COMPARISON_FILE,
        SAMPLE_FILE,
        REPORT_FILE,
    ]
    for path in required_files:
        if not path.exists():
            raise FileNotFoundError(path)

    source = pd.read_csv(
        WEEK6_FILE,
        usecols=[KEY_COLUMN, *TARGET_COLUMNS],
        low_memory=False,
    )
    flagged = pd.read_csv(
        FLAGGED_FILE,
        usecols=[
            KEY_COLUMN,
            *TARGET_COLUMNS,
            "close_price_iqr_outlier_flag",
            "close_price_extreme_percentile_flag",
            "close_price_business_rule_invalid_flag",
            "close_price_outlier_flag",
            "living_area_iqr_outlier_flag",
            "living_area_extreme_percentile_flag",
            "living_area_business_rule_invalid_flag",
            "living_area_outlier_flag",
            "days_on_market_iqr_outlier_flag",
            "days_on_market_extreme_percentile_flag",
            "days_on_market_business_rule_invalid_flag",
            "days_on_market_outlier_flag",
            "any_iqr_outlier_flag",
            "any_extreme_percentile_flag",
            "any_business_rule_invalid_flag",
            "outlier_flag_count",
            "any_outlier_flag",
            "duplicate_listing_key_group_flag",
            "superseded_duplicate_snapshot_flag",
            "analysis_exclusion_flag",
        ],
        low_memory=False,
    )
    clean = pd.read_csv(
        CLEAN_FILE,
        usecols=[
            KEY_COLUMN,
            *TARGET_COLUMNS,
            "any_outlier_flag",
            "superseded_duplicate_snapshot_flag",
            "analysis_exclusion_flag",
        ],
        low_memory=False,
    )
    summary = pd.read_csv(SUMMARY_FILE).set_index("field")
    comparison = pd.read_csv(COMPARISON_FILE).set_index("metric")

    if len(flagged) != len(source):
        raise AssertionError("The complete flagged dataset does not preserve all rows")
    if flagged[[KEY_COLUMN, *TARGET_COLUMNS]].fillna(-999999).equals(
        source[[KEY_COLUMN, *TARGET_COLUMNS]].fillna(-999999)
    ) is False:
        raise AssertionError("Source key or numeric values changed in flagged data")
    if clean["any_outlier_flag"].astype(bool).any():
        raise AssertionError("The clean dataset still contains outlier-flagged rows")
    if clean["superseded_duplicate_snapshot_flag"].astype(bool).any():
        raise AssertionError("The clean dataset contains superseded snapshots")
    if clean[KEY_COLUMN].duplicated(keep=False).any():
        raise AssertionError("The clean dataset is not unique by ListingKey")

    expected_clean_rows = int(
        (~flagged["analysis_exclusion_flag"].astype(bool)).sum()
    )
    if len(clean) != expected_clean_rows:
        raise AssertionError("Clean row count does not match the combined flag")

    expected_iqr_combined = pd.Series(False, index=flagged.index)
    expected_percentile_combined = pd.Series(False, index=flagged.index)
    expected_invalid_combined = pd.Series(False, index=flagged.index)
    expected_field_combined = pd.Series(False, index=flagged.index)
    expected_flag_count = pd.Series(0, index=flagged.index, dtype="int64")

    for column in TARGET_COLUMNS:
        prefix = FLAG_PREFIXES[column]
        values = pd.to_numeric(flagged[column], errors="coerce")
        limits = summary.loc[column]

        expected_iqr = values.notna() & (
            values.lt(limits["iqr_lower_bound"])
            | values.gt(limits["iqr_upper_bound"])
        )
        expected_percentile = values.notna() & (
            values.lt(limits["p001"]) | values.gt(limits["p999"])
        )
        if column in {"ClosePrice", "LivingArea"}:
            expected_invalid = values.notna() & values.le(0)
        else:
            expected_invalid = values.notna() & values.lt(0)
        expected_field = expected_iqr | expected_percentile | expected_invalid

        actual_iqr = flagged[f"{prefix}_iqr_outlier_flag"].astype(bool)
        actual_percentile = flagged[
            f"{prefix}_extreme_percentile_flag"
        ].astype(bool)
        actual_invalid = flagged[
            f"{prefix}_business_rule_invalid_flag"
        ].astype(bool)
        actual_field = flagged[f"{prefix}_outlier_flag"].astype(bool)

        if not actual_iqr.equals(expected_iqr):
            raise AssertionError(f"{column} IQR flags do not recompute")
        if not actual_percentile.equals(expected_percentile):
            raise AssertionError(f"{column} percentile flags do not recompute")
        if not actual_invalid.equals(expected_invalid):
            raise AssertionError(f"{column} business-rule flags do not recompute")
        if not actual_field.equals(expected_field):
            raise AssertionError(f"{column} combined flags do not recompute")

        expected_iqr_combined |= expected_iqr
        expected_percentile_combined |= expected_percentile
        expected_invalid_combined |= expected_invalid
        expected_field_combined |= expected_field
        expected_flag_count += expected_field.astype("int64")

        assert_close(
            float(source[column].median()),
            float(limits["source_median"]),
            f"{column} source median",
        )
        assert_close(
            float(clean[column].median()),
            float(limits["clean_median"]),
            f"{column} clean median",
        )

    combined_checks = {
        "any_iqr_outlier_flag": expected_iqr_combined,
        "any_extreme_percentile_flag": expected_percentile_combined,
        "any_business_rule_invalid_flag": expected_invalid_combined,
        "any_outlier_flag": expected_field_combined,
    }
    for column, expected in combined_checks.items():
        if not flagged[column].astype(bool).equals(expected):
            raise AssertionError(f"{column} does not recompute")
    if not flagged["outlier_flag_count"].astype("int64").equals(
        expected_flag_count
    ):
        raise AssertionError("outlier_flag_count does not recompute")

    expected_duplicate_group = flagged[KEY_COLUMN].duplicated(keep=False)
    expected_superseded = flagged[KEY_COLUMN].duplicated(keep="last")
    expected_analysis_exclusion = expected_field_combined | expected_superseded
    duplicate_checks = {
        "duplicate_listing_key_group_flag": expected_duplicate_group,
        "superseded_duplicate_snapshot_flag": expected_superseded,
        "analysis_exclusion_flag": expected_analysis_exclusion,
    }
    for column, expected in duplicate_checks.items():
        if not flagged[column].astype(bool).equals(expected):
            raise AssertionError(f"{column} does not recompute")

    if int(comparison.loc["row_count", "before_filtering"]) != len(source):
        raise AssertionError("Comparison source row count is incorrect")
    if int(comparison.loc["row_count", "after_filtering"]) != len(clean):
        raise AssertionError("Comparison clean row count is incorrect")

    sample = pd.read_csv(SAMPLE_FILE)
    if len(sample) != 25 or not sample["analysis_exclusion_flag"].astype(bool).all():
        raise AssertionError("Flagged sample is missing or contains unflagged rows")

    report_text = REPORT_FILE.read_text(encoding="utf-8")
    for required_heading in [
        "## Executive summary",
        "## Method",
        "## Dataset size comparison",
        "## Median comparison",
        "## Flag summary",
        "## Interpretation and limitations",
    ]:
        if required_heading not in report_text:
            raise AssertionError(f"Written comparison is missing {required_heading}")

    print(f"Source and flagged rows verified: {len(source):,}")
    print(f"Clean rows verified: {len(clean):,}")
    print(f"Excluded rows verified: {len(source) - len(clean):,}")
    print("All field and combined flags independently recomputed.")
    print("All required summaries and written-comparison sections verified.")
    print("Independent Week 7 validation passed.")


if __name__ == "__main__":
    main()
