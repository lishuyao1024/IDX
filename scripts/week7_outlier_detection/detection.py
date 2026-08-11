"""Week 7 outlier detection and data-quality filtering.

The script applies global 1.5 x IQR rules to ClosePrice, LivingArea, and
DaysOnMarket. It preserves every source row in a fully flagged dataset and
creates a separate analysis-ready dataset that excludes rows flagged by any
of the following transparent rules:

1. IQR outlier rule.
2. Extreme percentile rule (below p0.1 or above p99.9).
3. Stable business validity rule (non-positive price/area or negative DOM).

Missing values are reported but are not treated as outliers. Earlier cleaning
work owns missing-value remediation, while this script focuses on the Week 7
outlier requirement.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = (
    PROJECT_ROOT
    / "outputs"
    / "week6_feature_engineering"
    / "CRMLSSold_Residential_202401_202606_Week6_Engineered.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "week7_outlier_detection"

FLAGGED_FILE = (
    OUTPUT_DIR
    / "CRMLSSold_Residential_202401_202606_Week7_Flagged.csv"
)
CLEAN_FILE = (
    OUTPUT_DIR
    / "CRMLSSold_Residential_202401_202606_Week7_Clean_Filtered.csv"
)
OUTLIER_SUMMARY_FILE = OUTPUT_DIR / "week7_outlier_summary.csv"
DATASET_COMPARISON_FILE = OUTPUT_DIR / "week7_dataset_comparison.csv"
FLAGGED_SAMPLE_FILE = OUTPUT_DIR / "week7_flagged_sample.csv"
WRITTEN_COMPARISON_FILE = OUTPUT_DIR / "week7_before_after_comparison.md"

KEY_COLUMN = "ListingKey"
TARGET_COLUMNS = ["ClosePrice", "LivingArea", "DaysOnMarket"]
FLAG_PREFIXES = {
    "ClosePrice": "close_price",
    "LivingArea": "living_area",
    "DaysOnMarket": "days_on_market",
}
IQR_MULTIPLIER = 1.5
LOW_PERCENTILE = 0.001
HIGH_PERCENTILE = 0.999
CHUNK_SIZE = 50_000
SAMPLE_SIZE = 25


def validate_input() -> list[str]:
    """Confirm the Week 6 source exists and contains required fields."""
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Week 6 engineered input not found: {INPUT_FILE}")

    columns = pd.read_csv(INPUT_FILE, nrows=0).columns.tolist()
    required_columns = [KEY_COLUMN, *TARGET_COLUMNS]
    missing = sorted(set(required_columns).difference(columns))
    if missing:
        raise ValueError("Missing required input columns: " + ", ".join(missing))
    return columns


def business_rule_invalid(series: pd.Series, column: str) -> pd.Series:
    """Return stable, explicitly documented domain-invalid flags."""
    if column in {"ClosePrice", "LivingArea"}:
        return series.notna() & series.le(0)
    if column == "DaysOnMarket":
        return series.notna() & series.lt(0)
    raise KeyError(f"No business rule is defined for {column}")


def calculate_thresholds(profile: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Calculate global IQR and extreme-percentile thresholds."""
    thresholds: dict[str, dict[str, float]] = {}
    for column in TARGET_COLUMNS:
        series = profile[column]
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        thresholds[column] = {
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "iqr_lower_bound": q1 - IQR_MULTIPLIER * iqr,
            "iqr_upper_bound": q3 + IQR_MULTIPLIER * iqr,
            "p001": float(series.quantile(LOW_PERCENTILE)),
            "p999": float(series.quantile(HIGH_PERCENTILE)),
        }
    return thresholds


def build_flags(
    numeric_data: pd.DataFrame,
    thresholds: dict[str, dict[str, float]],
) -> pd.DataFrame:
    """Create field-level and combined outlier flags without deleting rows."""
    flags = pd.DataFrame(index=numeric_data.index)
    field_outlier_columns: list[str] = []
    iqr_columns: list[str] = []
    percentile_columns: list[str] = []
    invalid_columns: list[str] = []

    for column in TARGET_COLUMNS:
        prefix = FLAG_PREFIXES[column]
        series = numeric_data[column]
        limits = thresholds[column]

        iqr_name = f"{prefix}_iqr_outlier_flag"
        percentile_name = f"{prefix}_extreme_percentile_flag"
        invalid_name = f"{prefix}_business_rule_invalid_flag"
        outlier_name = f"{prefix}_outlier_flag"

        flags[iqr_name] = series.notna() & (
            series.lt(limits["iqr_lower_bound"])
            | series.gt(limits["iqr_upper_bound"])
        )
        flags[percentile_name] = series.notna() & (
            series.lt(limits["p001"]) | series.gt(limits["p999"])
        )
        flags[invalid_name] = business_rule_invalid(series, column)
        flags[outlier_name] = flags[
            [iqr_name, percentile_name, invalid_name]
        ].any(axis=1)

        iqr_columns.append(iqr_name)
        percentile_columns.append(percentile_name)
        invalid_columns.append(invalid_name)
        field_outlier_columns.append(outlier_name)

    flags["any_iqr_outlier_flag"] = flags[iqr_columns].any(axis=1)
    flags["any_extreme_percentile_flag"] = flags[percentile_columns].any(axis=1)
    flags["any_business_rule_invalid_flag"] = flags[invalid_columns].any(axis=1)
    flags["outlier_flag_count"] = flags[field_outlier_columns].sum(axis=1)
    flags["any_outlier_flag"] = flags[field_outlier_columns].any(axis=1)
    return flags


def add_grain_quality_flags(
    flags: pd.DataFrame,
    listing_keys: pd.Series,
) -> pd.DataFrame:
    """Flag repeated snapshots and define the analysis-level exclusion rule."""
    if listing_keys.isna().any():
        raise ValueError("ListingKey contains missing values; grain is not auditable")

    flags = flags.copy()
    flags["duplicate_listing_key_group_flag"] = listing_keys.duplicated(
        keep=False
    )
    # Monthly source files were appended oldest to newest. Keeping the last
    # occurrence preserves the newest available snapshot for a repeated key.
    flags["superseded_duplicate_snapshot_flag"] = listing_keys.duplicated(
        keep="last"
    )
    flags["analysis_exclusion_flag"] = (
        flags["any_outlier_flag"]
        | flags["superseded_duplicate_snapshot_flag"]
    )
    return flags


def create_outlier_summary(
    profile: pd.DataFrame,
    clean_profile: pd.DataFrame,
    flags: pd.DataFrame,
    thresholds: dict[str, dict[str, float]],
) -> pd.DataFrame:
    """Create field-level evidence for thresholds, flags, and medians."""
    rows: list[dict[str, object]] = []
    total_rows = len(profile)
    clean_rows = len(clean_profile)

    for column in TARGET_COLUMNS:
        prefix = FLAG_PREFIXES[column]
        before = profile[column]
        after = clean_profile[column]
        before_median = float(before.median())
        after_median = float(after.median())
        median_change = after_median - before_median
        median_change_pct = (
            median_change / before_median * 100
            if before_median != 0
            else np.nan
        )
        limits = thresholds[column]

        rows.append(
            {
                "field": column,
                "source_rows": total_rows,
                "clean_rows": clean_rows,
                "source_non_null": int(before.notna().sum()),
                "source_missing": int(before.isna().sum()),
                "clean_non_null": int(after.notna().sum()),
                "source_min": float(before.min()),
                "source_q1": limits["q1"],
                "source_median": before_median,
                "source_q3": limits["q3"],
                "source_max": float(before.max()),
                "iqr": limits["iqr"],
                "iqr_lower_bound": limits["iqr_lower_bound"],
                "iqr_upper_bound": limits["iqr_upper_bound"],
                "p001": limits["p001"],
                "p999": limits["p999"],
                "iqr_flagged_rows": int(
                    flags[f"{prefix}_iqr_outlier_flag"].sum()
                ),
                "extreme_percentile_flagged_rows": int(
                    flags[f"{prefix}_extreme_percentile_flag"].sum()
                ),
                "business_rule_invalid_rows": int(
                    flags[f"{prefix}_business_rule_invalid_flag"].sum()
                ),
                "combined_field_flagged_rows": int(
                    flags[f"{prefix}_outlier_flag"].sum()
                ),
                "combined_field_flagged_pct": float(
                    flags[f"{prefix}_outlier_flag"].mean() * 100
                ),
                "clean_median": after_median,
                "median_change": median_change,
                "median_change_pct": median_change_pct,
            }
        )

    return pd.DataFrame(rows)


def create_dataset_comparison(
    profile: pd.DataFrame,
    clean_profile: pd.DataFrame,
    flags: pd.DataFrame,
) -> pd.DataFrame:
    """Create the required before/after dataset-size comparison."""
    source_rows = len(profile)
    clean_rows = len(clean_profile)
    removed_rows = source_rows - clean_rows
    outlier_rows = int(flags["any_outlier_flag"].sum())
    superseded_rows = int(flags["superseded_duplicate_snapshot_flag"].sum())
    overlap_rows = int(
        (
            flags["any_outlier_flag"]
            & flags["superseded_duplicate_snapshot_flag"]
        ).sum()
    )

    rows: list[dict[str, object]] = [
        {
            "metric": "row_count",
            "before_filtering": source_rows,
            "after_filtering": clean_rows,
            "absolute_change": clean_rows - source_rows,
            "percent_change": (clean_rows - source_rows) / source_rows * 100,
        },
        {
            "metric": "rows_removed",
            "before_filtering": 0,
            "after_filtering": removed_rows,
            "absolute_change": removed_rows,
            "percent_change": removed_rows / source_rows * 100,
        },
    ]

    for column in TARGET_COLUMNS:
        before_median = float(profile[column].median())
        after_median = float(clean_profile[column].median())
        change = after_median - before_median
        rows.append(
            {
                "metric": f"median_{column}",
                "before_filtering": before_median,
                "after_filtering": after_median,
                "absolute_change": change,
                "percent_change": (
                    change / before_median * 100
                    if before_median != 0
                    else np.nan
                ),
            }
        )

    rows.extend(
        [
            {
                "metric": "rows_with_any_iqr_outlier",
                "before_filtering": int(flags["any_iqr_outlier_flag"].sum()),
                "after_filtering": 0,
                "absolute_change": -int(flags["any_iqr_outlier_flag"].sum()),
                "percent_change": np.nan,
            },
            {
                "metric": "rows_with_any_extreme_percentile",
                "before_filtering": int(
                    flags["any_extreme_percentile_flag"].sum()
                ),
                "after_filtering": 0,
                "absolute_change": -int(
                    flags["any_extreme_percentile_flag"].sum()
                ),
                "percent_change": np.nan,
            },
            {
                "metric": "rows_with_any_business_rule_invalid",
                "before_filtering": int(
                    flags["any_business_rule_invalid_flag"].sum()
                ),
                "after_filtering": 0,
                "absolute_change": -int(
                    flags["any_business_rule_invalid_flag"].sum()
                ),
                "percent_change": np.nan,
            },
            {
                "metric": "rows_with_any_combined_outlier",
                "before_filtering": outlier_rows,
                "after_filtering": 0,
                "absolute_change": -outlier_rows,
                "percent_change": np.nan,
            },
            {
                "metric": "rows_in_duplicate_listing_key_groups",
                "before_filtering": int(
                    flags["duplicate_listing_key_group_flag"].sum()
                ),
                "after_filtering": 0,
                "absolute_change": -int(
                    flags["duplicate_listing_key_group_flag"].sum()
                ),
                "percent_change": np.nan,
            },
            {
                "metric": "superseded_duplicate_snapshots_excluded",
                "before_filtering": superseded_rows,
                "after_filtering": 0,
                "absolute_change": -superseded_rows,
                "percent_change": np.nan,
            },
            {
                "metric": "outlier_and_superseded_overlap",
                "before_filtering": overlap_rows,
                "after_filtering": 0,
                "absolute_change": -overlap_rows,
                "percent_change": np.nan,
            },
            {
                "metric": "rows_with_any_analysis_exclusion",
                "before_filtering": removed_rows,
                "after_filtering": 0,
                "absolute_change": -removed_rows,
                "percent_change": np.nan,
            },
        ]
    )
    return pd.DataFrame(rows)


def format_number(value: float, field: str) -> str:
    """Format report values with units that match each field."""
    if field == "ClosePrice":
        sign = "-" if value < 0 else ""
        return f"{sign}${abs(value):,.2f}"
    if field == "LivingArea":
        return f"{value:,.2f} sq ft"
    return f"{value:,.2f} days"


def write_comparison_report(
    outlier_summary: pd.DataFrame,
    dataset_comparison: pd.DataFrame,
    flags: pd.DataFrame,
) -> None:
    """Write the handbook-required comparison as a concise Markdown report."""
    row_record = dataset_comparison.loc[
        dataset_comparison["metric"].eq("row_count")
    ].iloc[0]
    source_rows = int(row_record["before_filtering"])
    clean_rows = int(row_record["after_filtering"])
    removed_rows = source_rows - clean_rows
    removed_pct = removed_rows / source_rows * 100
    outlier_rows = int(flags["any_outlier_flag"].sum())
    superseded_rows = int(flags["superseded_duplicate_snapshot_flag"].sum())
    overlap_exclusions = int(
        (
            flags["any_outlier_flag"]
            & flags["superseded_duplicate_snapshot_flag"]
        ).sum()
    )

    lines = [
        "# Week 7 - Outlier Detection Before/After Comparison",
        "",
        "## Executive summary",
        "",
        (
            f"The Week 7 process evaluated {source_rows:,} residential sold "
            f"records and retained {clean_rows:,} records in the clean analysis "
            f"dataset. A total of {removed_rows:,} rows ({removed_pct:.2f}%) "
            "were excluded from the separate clean dataset because at least one "
            "key numeric field was flagged or the row was a superseded duplicate "
            "snapshot. The complete flagged dataset still preserves every source "
            "record."
        ),
        "",
        "## Method",
        "",
        (
            "For ClosePrice, LivingArea, and DaysOnMarket, the script calculated "
            "Q1, Q3, IQR, and the standard 1.5 x IQR bounds. It also recorded "
            "extreme percentile flags below p0.1 or above p99.9 because strongly "
            "right-skewed housing measures can produce negative IQR lower bounds "
            "that fail to identify implausibly small positive values."
        ),
        "",
        (
            "Business validity flags are separate and transparent: ClosePrice "
            "and LivingArea must be greater than zero, while DaysOnMarket must "
            "be zero or greater. Missing values are reported but are not treated "
            "as outliers in this Week 7 workflow."
        ),
        "",
        (
            "The intended downstream grain is one row per ListingKey. Repeated "
            "ListingKey snapshots remain visible in the complete flagged file, "
            "while the clean file keeps the last (newest loaded) snapshot."
        ),
        "",
        "## Dataset size comparison",
        "",
        "| Measure | Before | After | Change |",
        "|---|---:|---:|---:|",
        (
            f"| Rows | {source_rows:,} | {clean_rows:,} | "
            f"-{removed_rows:,} ({removed_pct:.2f}%) |"
        ),
        (
            f"| Numeric outlier rows | {outlier_rows:,} | 0 | "
            f"-{outlier_rows:,} |"
        ),
        (
            f"| Superseded duplicate snapshots | {superseded_rows:,} | 0 | "
            f"-{superseded_rows:,} |"
        ),
        "",
        "## Median comparison",
        "",
        "| Field | Before median | After median | Change |",
        "|---|---:|---:|---:|",
    ]

    for _, record in outlier_summary.iterrows():
        field = str(record["field"])
        before = float(record["source_median"])
        after = float(record["clean_median"])
        change = float(record["median_change"])
        change_pct = float(record["median_change_pct"])
        lines.append(
            f"| {field} | {format_number(before, field)} | "
            f"{format_number(after, field)} | "
            f"{format_number(change, field)} ({change_pct:+.2f}%) |"
        )

    lines.extend(
        [
            "",
            "## Flag summary",
            "",
            "| Field | IQR flags | Extreme-percentile flags | "
            "Business-rule invalid | Combined field flags |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for _, record in outlier_summary.iterrows():
        lines.append(
            f"| {record['field']} | {int(record['iqr_flagged_rows']):,} | "
            f"{int(record['extreme_percentile_flagged_rows']):,} | "
            f"{int(record['business_rule_invalid_rows']):,} | "
            f"{int(record['combined_field_flagged_rows']):,} |"
        )

    overlap_rows = int((flags["outlier_flag_count"] > 1).sum())
    lines.extend(
        [
            "",
            (
                f"Because one row can be flagged in more than one field, field "
                f"counts do not add directly to the {outlier_rows:,} unique "
                f"numeric-outlier rows. {overlap_rows:,} rows were flagged in "
                "multiple fields."
            ),
            "",
            (
                f"The dataset also contained {superseded_rows:,} older duplicate "
                f"snapshots; {overlap_exclusions:,} of those were already numeric "
                "outliers. Exclusion totals therefore use the union of the two "
                "conditions rather than adding their counts."
            ),
            "",
            "## Interpretation and limitations",
            "",
            (
                "The clean dataset is appropriate for typical-market summaries "
                "and the next Tableau phase. The flagged dataset should remain "
                "the audit source for luxury, distressed-sale, and data-quality "
                "review because a statistical outlier is not automatically an "
                "incorrect transaction."
            ),
            "",
            (
                "The thresholds are global across the full residential sold "
                "dataset. Property-subtype or geographic analyses may later use "
                "segment-specific thresholds if the business question requires "
                "them, but those alternate thresholds should not silently replace "
                "the Week 7 global method."
            ),
            "",
        ]
    )
    WRITTEN_COMPARISON_FILE.write_text("\n".join(lines), encoding="utf-8")


def write_large_outputs(
    flags: pd.DataFrame,
    source_columns: list[str],
) -> None:
    """Stream the full source into flagged and filtered CSV outputs."""
    for path in [FLAGGED_FILE, CLEAN_FILE]:
        if path.exists():
            path.unlink()

    flag_columns = flags.columns.tolist()
    first_chunk = True
    offset = 0
    flagged_sample_parts: list[pd.DataFrame] = []
    sample_rows_remaining = SAMPLE_SIZE

    for chunk_number, chunk in enumerate(
        pd.read_csv(INPUT_FILE, chunksize=CHUNK_SIZE, low_memory=False),
        start=1,
    ):
        chunk_size = len(chunk)
        chunk_flags = flags.iloc[offset : offset + chunk_size].reset_index(drop=True)
        chunk = chunk.reset_index(drop=True)
        if chunk.columns.tolist() != source_columns:
            raise AssertionError("Source column order changed during chunked read")

        flagged_chunk = pd.concat([chunk, chunk_flags], axis=1)
        flagged_chunk.to_csv(
            FLAGGED_FILE,
            mode="w" if first_chunk else "a",
            header=first_chunk,
            index=False,
        )

        clean_mask = ~chunk_flags["analysis_exclusion_flag"]
        flagged_chunk.loc[clean_mask].to_csv(
            CLEAN_FILE,
            mode="w" if first_chunk else "a",
            header=first_chunk,
            index=False,
        )

        if sample_rows_remaining > 0:
            sample_candidates = flagged_chunk.loc[
                ~clean_mask,
                [
                    "ListingKey",
                    *TARGET_COLUMNS,
                    *flag_columns,
                ],
            ].head(sample_rows_remaining)
            if not sample_candidates.empty:
                flagged_sample_parts.append(sample_candidates)
                sample_rows_remaining -= len(sample_candidates)

        offset += chunk_size
        first_chunk = False
        print(
            f"Processed chunk {chunk_number}: {offset:,} / {len(flags):,} rows"
        )

    if offset != len(flags):
        raise AssertionError(
            f"Chunked output wrote {offset:,} rows; expected {len(flags):,}"
        )

    if flagged_sample_parts:
        pd.concat(flagged_sample_parts, ignore_index=True).to_csv(
            FLAGGED_SAMPLE_FILE,
            index=False,
        )
    else:
        pd.DataFrame(columns=["ListingKey", *TARGET_COLUMNS, *flag_columns]).to_csv(
            FLAGGED_SAMPLE_FILE,
            index=False,
        )


def main() -> None:
    source_columns = validate_input()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_profile = pd.read_csv(
        INPUT_FILE,
        usecols=[KEY_COLUMN, *TARGET_COLUMNS],
        low_memory=False,
    )
    profile = source_profile[TARGET_COLUMNS].apply(
        pd.to_numeric,
        errors="coerce",
    )
    thresholds = calculate_thresholds(profile)
    flags = build_flags(profile, thresholds)
    flags = add_grain_quality_flags(flags, source_profile[KEY_COLUMN])
    clean_profile = profile.loc[~flags["analysis_exclusion_flag"]].copy()

    outlier_summary = create_outlier_summary(
        profile,
        clean_profile,
        flags,
        thresholds,
    )
    dataset_comparison = create_dataset_comparison(profile, clean_profile, flags)

    write_large_outputs(flags, source_columns)
    outlier_summary.round(6).to_csv(OUTLIER_SUMMARY_FILE, index=False)
    dataset_comparison.round(6).to_csv(DATASET_COMPARISON_FILE, index=False)
    write_comparison_report(outlier_summary, dataset_comparison, flags)

    removed_rows = int(flags["analysis_exclusion_flag"].sum())
    print(f"Source rows preserved in flagged dataset: {len(profile):,}")
    print(f"Rows in clean filtered dataset: {len(clean_profile):,}")
    print(f"Rows excluded from clean dataset: {removed_rows:,}")
    print("Week 7 outlier detection completed successfully.")


if __name__ == "__main__":
    main()
