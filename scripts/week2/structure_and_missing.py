"""
Weeks 2-3: dataset structure and missing-value review.

Uses the Week 1 combined Residential Sold and Listing CSV files. It does not
recombine monthly files and does not perform numeric-distribution or mortgage
rate analysis.

Outputs are clearly separated with sold_ and listing_ filename prefixes.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd


DATASETS = {
    "sold": "CRMLSSold_Residential_202401_202605.csv",
    "listing": "CRMLSListing_Residential_202401_202605.csv",
}


def analyze_dataset(
    dataset_name: str,
    input_path: Path,
    output_dir: Path,
    chunksize: int,
) -> None:
    """Create structure, preview, property-type, and null reports for one CSV."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # A sample is sufficient for readable inferred data types and preview rows.
    sample = pd.read_csv(input_path, nrows=10_000, low_memory=False)
    if "PropertyType" not in sample.columns:
        raise KeyError(f"PropertyType is missing from {input_path.name}")

    sample.head(5).to_csv(
        output_dir / f"{dataset_name}_head.csv",
        index=False,
        encoding="utf-8-sig",
    )

    row_count = 0
    null_counts = pd.Series(0, index=sample.columns, dtype="int64")
    property_type_counts: Counter[str] = Counter()

    for chunk in pd.read_csv(input_path, chunksize=chunksize, low_memory=False):
        row_count += len(chunk)
        null_counts = null_counts.add(chunk.isna().sum(), fill_value=0)

        property_types = chunk["PropertyType"].astype("string").str.strip()
        displayed = property_types.fillna("<MISSING>").replace("", "<BLANK>")
        property_type_counts.update(displayed.tolist())

    column_count = len(sample.columns)
    property_types = sorted(property_type_counts)
    residential_only = property_types == ["Residential"]

    overview = pd.DataFrame(
        [
            {
                "dataset": dataset_name,
                "source_file": input_path.name,
                "row_count": row_count,
                "column_count": column_count,
                "property_type_unique_count": len(property_types),
                "residential_only": residential_only,
                "filter_confirmation": (
                    "Confirmed: all rows are Residential"
                    if residential_only
                    else "Review required: non-Residential values found"
                ),
            }
        ]
    )
    overview.to_csv(
        output_dir / f"{dataset_name}_dataset_overview.csv",
        index=False,
        encoding="utf-8-sig",
    )

    structure = pd.DataFrame(
        {
            "column_position": range(1, column_count + 1),
            "column": sample.columns,
            "sample_inferred_dtype": [str(dtype) for dtype in sample.dtypes],
        }
    )
    structure.to_csv(
        output_dir / f"{dataset_name}_column_structure.csv",
        index=False,
        encoding="utf-8-sig",
    )

    property_report = pd.DataFrame(
        [
            {
                "property_type": property_type,
                "row_count": count,
                "percentage": count / row_count * 100,
            }
            for property_type, count in sorted(
                property_type_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ]
    )
    property_report.to_csv(
        output_dir / f"{dataset_name}_property_types.csv",
        index=False,
        encoding="utf-8-sig",
        float_format="%.4f",
    )

    null_summary = pd.DataFrame(
        {
            "column": sample.columns,
            "null_count": [int(null_counts[column]) for column in sample.columns],
        }
    )
    null_summary["non_null_count"] = row_count - null_summary["null_count"]
    null_summary["null_percentage"] = (
        null_summary["null_count"] / row_count * 100
    )
    null_summary["above_90_percent_null"] = (
        null_summary["null_percentage"] > 90
    )
    null_summary = null_summary.sort_values(
        ["null_percentage", "column"], ascending=[False, True]
    )
    null_summary.to_csv(
        output_dir / f"{dataset_name}_null_summary.csv",
        index=False,
        encoding="utf-8-sig",
        float_format="%.4f",
    )
    null_summary.loc[null_summary["above_90_percent_null"]].to_csv(
        output_dir / f"{dataset_name}_missing_above_90_percent.csv",
        index=False,
        encoding="utf-8-sig",
        float_format="%.4f",
    )

    print(
        f"{dataset_name.upper()}: {row_count:,} rows, {column_count} columns, "
        f"{len(property_types)} PropertyType value(s), "
        f"{int(null_summary['above_90_percent_null'].sum())} columns above 90% null."
    )


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=script_dir / "outputs" / "week1",
        help="Folder containing the Week 1 combined CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=script_dir / "outputs" / "week2_3_structure_missing",
        help="Folder for the separate Sold and Listing reports.",
    )
    parser.add_argument("--chunksize", type=int, default=50_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.chunksize <= 0:
        raise ValueError("chunksize must be greater than zero.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for dataset_name, filename in DATASETS.items():
        analyze_dataset(
            dataset_name=dataset_name,
            input_path=args.input_dir / filename,
            output_dir=args.output_dir,
            chunksize=args.chunksize,
        )

    print(f"Reports saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
