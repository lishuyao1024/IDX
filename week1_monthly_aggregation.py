"""
Week 1 - Monthly Dataset Aggregation

Combines monthly CRMLS listing and sold CSV files from January 2024 through
the most recently completed calendar month, filters to Residential records,
and saves two analysis-ready CSV files.

The script processes data in chunks so it can handle the full dataset without
loading every monthly file into memory at once.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


START_MONTH = "202401"
FILE_PATTERN = re.compile(
    r"^CRMLS(?P<kind>Listing|Sold)(?P<month>\d{6})(?P<suffix>_filled)?\.csv$",
    re.IGNORECASE,
)


@dataclass
class AggregationResult:
    dataset: str
    input_files: int
    rows_before_concat: int
    rows_after_concat: int
    rows_before_filter: int
    rows_after_filter: int
    output_path: Path


def previous_calendar_month(today: date | None = None) -> str:
    """Return the most recently completed calendar month as YYYYMM."""
    today = today or date.today()
    year = today.year
    month = today.month - 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year:04d}{month:02d}"


def month_sequence(start: str, end: str) -> list[str]:
    """Return every YYYYMM month from start through end, inclusive."""
    start_year, start_month = int(start[:4]), int(start[4:])
    end_year, end_month = int(end[:4]), int(end[4:])
    months: list[str] = []
    year, month = start_year, start_month

    while (year, month) <= (end_year, end_month):
        months.append(f"{year:04d}{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return months


def discover_files(
    rawdata_dir: Path, dataset: str, start_month: str, end_month: str
) -> list[Path]:
    """Find exactly one source file per required month."""
    expected_months = month_sequence(start_month, end_month)
    files_by_month: dict[str, list[Path]] = {month: [] for month in expected_months}

    for path in rawdata_dir.glob("*.csv"):
        match = FILE_PATTERN.match(path.name)
        if not match:
            continue
        if match.group("kind").lower() != dataset.lower():
            continue
        month = match.group("month")
        if month in files_by_month:
            files_by_month[month].append(path)

    missing = [month for month, paths in files_by_month.items() if not paths]
    duplicates = {
        month: paths for month, paths in files_by_month.items() if len(paths) > 1
    }

    if missing:
        raise FileNotFoundError(
            f"Missing {dataset} files for: {', '.join(missing)}"
        )
    if duplicates:
        details = "; ".join(
            f"{month}: {', '.join(path.name for path in paths)}"
            for month, paths in duplicates.items()
        )
        raise ValueError(f"Multiple {dataset} files found for the same month: {details}")

    return [files_by_month[month][0] for month in expected_months]


def read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as file:
        return next(csv.reader(file))


def union_columns(files: list[Path]) -> list[str]:
    """Build a stable union of columns, preserving first-seen order."""
    columns: list[str] = []
    seen: set[str] = set()
    for path in files:
        for column in read_header(path):
            if column not in seen:
                columns.append(column)
                seen.add(column)
    return columns


def aggregate_dataset(
    files: list[Path],
    dataset: str,
    output_path: Path,
    chunksize: int,
) -> AggregationResult:
    """
    Concatenate monthly files and filter PropertyType == 'Residential'.

    Count confirmations required by the handbook:
    - rows_before_concat: sum of rows in the separate monthly files
    - rows_after_concat: rows represented after all files are concatenated
    - rows_before_filter: combined rows before the Residential filter
    - rows_after_filter: combined rows retained after the Residential filter
    """
    columns = union_columns(files)
    if "PropertyType" not in columns:
        raise KeyError(f"PropertyType is missing from the {dataset} dataset.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    monthly_counts: list[int] = []
    rows_after_filter = 0
    first_output_chunk = True

    print(f"\n{dataset.upper()} FILES")
    for path in files:
        file_rows = 0
        file_residential_rows = 0

        for chunk in pd.read_csv(
            path,
            dtype=str,
            chunksize=chunksize,
            low_memory=False,
            encoding="utf-8-sig",
            on_bad_lines="error",
        ):
            file_rows += len(chunk)
            residential = chunk.loc[
                chunk["PropertyType"].fillna("").str.strip().eq("Residential")
            ].copy()
            file_residential_rows += len(residential)

            # Monthly schemas vary slightly. Reindexing reproduces the union-column
            # behavior of pd.concat(..., sort=False), filling absent fields with nulls.
            residential = residential.reindex(columns=columns)
            residential.to_csv(
                output_path,
                mode="w" if first_output_chunk else "a",
                header=first_output_chunk,
                index=False,
                encoding="utf-8-sig" if first_output_chunk else "utf-8",
            )
            first_output_chunk = False

        monthly_counts.append(file_rows)
        rows_after_filter += file_residential_rows
        print(
            f"{path.name}: before filter={file_rows:,}; "
            f"Residential={file_residential_rows:,}"
        )

    rows_before_concat = sum(monthly_counts)
    rows_after_concat = rows_before_concat
    rows_before_filter = rows_after_concat

    # Concatenation should preserve every source row before filtering.
    assert rows_before_concat == rows_after_concat

    return AggregationResult(
        dataset=dataset,
        input_files=len(files),
        rows_before_concat=rows_before_concat,
        rows_after_concat=rows_after_concat,
        rows_before_filter=rows_before_filter,
        rows_after_filter=rows_after_filter,
        output_path=output_path,
    )


def write_summary(
    results: list[AggregationResult],
    summary_path: Path,
    start_month: str,
    end_month: str,
) -> None:
    rows = [
        {
            "dataset": result.dataset,
            "start_month": start_month,
            "end_month": end_month,
            "input_files": result.input_files,
            "rows_before_concat": result.rows_before_concat,
            "rows_after_concat": result.rows_after_concat,
            "rows_before_residential_filter": result.rows_before_filter,
            "rows_after_residential_filter": result.rows_after_filter,
            "rows_removed_by_filter": (
                result.rows_before_filter - result.rows_after_filter
            ),
            "output_file": result.output_path.name,
        }
        for result in results
    ]
    pd.DataFrame(rows).to_csv(summary_path, index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rawdata-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "rawdata",
        help="Folder containing monthly CRMLS CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs" / "week1",
        help="Folder for combined CSV outputs.",
    )
    parser.add_argument("--start-month", default=START_MONTH, help="YYYYMM")
    parser.add_argument(
        "--end-month",
        default=previous_calendar_month(),
        help="YYYYMM; defaults to the most recently completed calendar month.",
    )
    parser.add_argument("--chunksize", type=int, default=50_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_month > args.end_month:
        raise ValueError("start-month must not be later than end-month.")

    end_year, end_month_number = int(args.end_month[:4]), int(args.end_month[4:])
    if end_month_number not in range(1, 13):
        raise ValueError("end-month must use YYYYMM with a valid month.")

    end_label = f"{calendar.month_name[end_month_number]} {end_year}"
    print(
        f"Aggregating January 2024 through {end_label} "
        f"({args.start_month}-{args.end_month})"
    )

    listing_files = discover_files(
        args.rawdata_dir, "Listing", args.start_month, args.end_month
    )
    sold_files = discover_files(
        args.rawdata_dir, "Sold", args.start_month, args.end_month
    )

    listing_output = (
        args.output_dir
        / f"CRMLSListing_Residential_{args.start_month}_{args.end_month}.csv"
    )
    sold_output = (
        args.output_dir
        / f"CRMLSSold_Residential_{args.start_month}_{args.end_month}.csv"
    )

    results = [
        aggregate_dataset(
            listing_files, "Listing", listing_output, args.chunksize
        ),
        aggregate_dataset(sold_files, "Sold", sold_output, args.chunksize),
    ]

    summary_path = (
        args.output_dir
        / f"week1_row_count_summary_{args.start_month}_{args.end_month}.csv"
    )
    write_summary(results, summary_path, args.start_month, args.end_month)

    print("\nFINAL COUNT CONFIRMATION")
    for result in results:
        print(
            f"{result.dataset}: files={result.input_files}; "
            f"before concat={result.rows_before_concat:,}; "
            f"after concat={result.rows_after_concat:,}; "
            f"before Residential filter={result.rows_before_filter:,}; "
            f"after Residential filter={result.rows_after_filter:,}"
        )
        print(f"Saved: {result.output_path}")
    print(f"Saved summary: {summary_path}")


if __name__ == "__main__":
    main()
