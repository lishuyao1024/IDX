"""
Week 3 - Mortgage Rate Enrichment

Fetches the FRED MORTGAGE30US weekly series, calculates calendar-month
average rates, and left-merges the monthly rate onto the combined Residential
Sold and Listing datasets created in Week 1.

The large MLS files are processed in chunks so identifiers and ZIP codes can
remain text and the full datasets do not need to fit in memory at once.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
RATE_COLUMN = "rate_30yr_fixed"
MONTH_COLUMN = "year_month"


@dataclass
class EnrichmentResult:
    dataset: str
    date_column: str
    input_rows: int
    output_rows: int
    invalid_date_rows: int
    unmatched_rate_rows: int
    first_month: str
    last_month: str
    output_path: Path


def fetch_monthly_mortgage_rates(url: str = FRED_URL) -> pd.DataFrame:
    """Fetch FRED's weekly 30-year fixed rate and calculate monthly averages."""
    mortgage = pd.read_csv(
        url,
        parse_dates=["observation_date"],
        na_values=["."],
    )

    required = {"observation_date", "MORTGAGE30US"}
    missing = required.difference(mortgage.columns)
    if missing:
        raise KeyError(f"FRED response is missing columns: {sorted(missing)}")

    mortgage = mortgage.rename(
        columns={
            "observation_date": "date",
            "MORTGAGE30US": RATE_COLUMN,
        }
    )
    mortgage[RATE_COLUMN] = pd.to_numeric(
        mortgage[RATE_COLUMN], errors="coerce"
    )
    mortgage = mortgage.dropna(subset=["date", RATE_COLUMN]).copy()
    mortgage[MONTH_COLUMN] = mortgage["date"].dt.to_period("M")

    mortgage_monthly = (
        mortgage.groupby(MONTH_COLUMN, as_index=False)[RATE_COLUMN]
        .mean()
        .sort_values(MONTH_COLUMN)
        .reset_index(drop=True)
    )

    if mortgage_monthly.empty:
        raise ValueError("FRED returned no usable mortgage-rate observations.")
    if mortgage_monthly[MONTH_COLUMN].duplicated().any():
        raise ValueError("Monthly FRED data contains duplicate year_month keys.")

    return mortgage_monthly


def enrich_dataset(
    input_path: Path,
    output_path: Path,
    dataset: str,
    date_column: str,
    mortgage_monthly: pd.DataFrame,
    chunksize: int,
) -> EnrichmentResult:
    """Left-merge one MLS CSV with monthly rates and validate the result."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if temporary_path.exists():
        temporary_path.unlink()

    input_rows = 0
    output_rows = 0
    invalid_date_rows = 0
    unmatched_rate_rows = 0
    first_period: pd.Period | None = None
    last_period: pd.Period | None = None
    first_output_chunk = True

    try:
        for chunk_number, chunk in enumerate(
            pd.read_csv(
                input_path,
                dtype=str,
                chunksize=chunksize,
                low_memory=False,
                encoding="utf-8-sig",
                on_bad_lines="error",
            ),
            start=1,
        ):
            if date_column not in chunk.columns:
                raise KeyError(
                    f"{date_column} is missing from the {dataset} dataset."
                )
            conflicts = {MONTH_COLUMN, RATE_COLUMN}.intersection(chunk.columns)
            if conflicts:
                raise ValueError(
                    f"{dataset} already contains enrichment columns: "
                    f"{sorted(conflicts)}"
                )

            input_rows += len(chunk)
            transaction_dates = pd.to_datetime(
                chunk[date_column], errors="coerce"
            )
            invalid_date_rows += int(transaction_dates.isna().sum())
            chunk[MONTH_COLUMN] = transaction_dates.dt.to_period("M")

            valid_periods = chunk[MONTH_COLUMN].dropna()
            if not valid_periods.empty:
                chunk_min = valid_periods.min()
                chunk_max = valid_periods.max()
                first_period = (
                    chunk_min
                    if first_period is None or chunk_min < first_period
                    else first_period
                )
                last_period = (
                    chunk_max
                    if last_period is None or chunk_max > last_period
                    else last_period
                )

            enriched = chunk.merge(
                mortgage_monthly,
                on=MONTH_COLUMN,
                how="left",
                sort=False,
                validate="many_to_one",
            )
            if len(enriched) != len(chunk):
                raise AssertionError(
                    f"{dataset} row count changed during the merge: "
                    f"{len(chunk):,} -> {len(enriched):,}"
                )

            output_rows += len(enriched)
            unmatched_rate_rows += int(enriched[RATE_COLUMN].isna().sum())
            enriched.to_csv(
                temporary_path,
                mode="w" if first_output_chunk else "a",
                header=first_output_chunk,
                index=False,
                encoding="utf-8-sig" if first_output_chunk else "utf-8",
            )
            first_output_chunk = False
            print(
                f"{dataset}: processed chunk {chunk_number:,}; "
                f"cumulative rows={input_rows:,}"
            )

        if input_rows == 0:
            raise ValueError(f"{dataset} input file contains no rows.")
        if input_rows != output_rows:
            raise AssertionError(
                f"{dataset} total row count changed: "
                f"{input_rows:,} -> {output_rows:,}"
            )
        if unmatched_rate_rows:
            raise ValueError(
                f"{dataset} has {unmatched_rate_rows:,} null mortgage-rate "
                f"values after the merge ({invalid_date_rows:,} rows have an "
                f"invalid or missing {date_column})."
            )

        temporary_path.replace(output_path)
    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()
        raise

    return EnrichmentResult(
        dataset=dataset,
        date_column=date_column,
        input_rows=input_rows,
        output_rows=output_rows,
        invalid_date_rows=invalid_date_rows,
        unmatched_rate_rows=unmatched_rate_rows,
        first_month=str(first_period),
        last_month=str(last_period),
        output_path=output_path,
    )


def write_validation_summary(
    results: list[EnrichmentResult],
    mortgage_monthly: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save the checks needed to audit the two completed merges."""
    fred_first_month = str(mortgage_monthly[MONTH_COLUMN].min())
    fred_last_month = str(mortgage_monthly[MONTH_COLUMN].max())
    rows = [
        {
            "dataset": result.dataset,
            "date_key": result.date_column,
            "input_rows": result.input_rows,
            "output_rows": result.output_rows,
            "row_count_unchanged": result.input_rows == result.output_rows,
            "invalid_or_missing_date_rows": result.invalid_date_rows,
            "null_rate_rows_after_merge": result.unmatched_rate_rows,
            "validation_passed": result.unmatched_rate_rows == 0,
            "dataset_first_month": result.first_month,
            "dataset_last_month": result.last_month,
            "fred_first_month": fred_first_month,
            "fred_last_month": fred_last_month,
            "output_file": result.output_path.name,
        }
        for result in results
    ]
    pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    week1_dir = project_root / "outputs" / "week1"
    output_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sold-input",
        type=Path,
        default=week1_dir / "CRMLSSold_Residential_202401_202606.csv",
    )
    parser.add_argument(
        "--listings-input",
        type=Path,
        default=week1_dir / "CRMLSListing_Residential_202401_202606.csv",
    )
    parser.add_argument("--output-dir", type=Path, default=output_dir)
    parser.add_argument("--fred-url", default=FRED_URL)
    parser.add_argument("--chunksize", type=int, default=50_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.chunksize <= 0:
        raise ValueError("chunksize must be greater than zero.")

    print(f"Fetching weekly mortgage rates from FRED:\n{args.fred_url}")
    mortgage_monthly = fetch_monthly_mortgage_rates(args.fred_url)
    print(
        "Monthly mortgage-rate coverage: "
        f"{mortgage_monthly[MONTH_COLUMN].min()} through "
        f"{mortgage_monthly[MONTH_COLUMN].max()} "
        f"({len(mortgage_monthly):,} months)"
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sold_output = args.output_dir / (
        f"{args.sold_input.stem}_Mortgage_Enriched.csv"
    )
    listings_output = args.output_dir / (
        f"{args.listings_input.stem}_Mortgage_Enriched.csv"
    )

    results = [
        enrich_dataset(
            args.sold_input,
            sold_output,
            "Sold",
            "CloseDate",
            mortgage_monthly,
            args.chunksize,
        ),
        enrich_dataset(
            args.listings_input,
            listings_output,
            "Listings",
            "ListingContractDate",
            mortgage_monthly,
            args.chunksize,
        ),
    ]

    summary_path = args.output_dir / "week3_mortgage_enrichment_validation.csv"
    write_validation_summary(results, mortgage_monthly, summary_path)

    print("\nFINAL VALIDATION")
    for result in results:
        print(
            f"{result.dataset}: input={result.input_rows:,}; "
            f"output={result.output_rows:,}; "
            f"invalid dates={result.invalid_date_rows:,}; "
            f"null rates={result.unmatched_rate_rows:,}; "
            f"months={result.first_month} to {result.last_month}"
        )
        print(f"Saved: {result.output_path}")
    print(f"Saved validation summary: {summary_path}")


if __name__ == "__main__":
    main()

dataset,date_key,input_rows,output_rows,row_count_unchanged,invalid_or_missing_date_rows,null_rate_rows_after_merge,validation_passed,dataset_first_month,dataset_last_month,fred_first_month,fred_last_month,output_file
Sold,CloseDate,447990,447990,True,0,0,True,2024-01,2026-06,1971-04,2026-07,CRMLSSold_Residential_202401_202606_Mortgage_Enriched.csv
Listings,ListingContractDate,616099,616099,True,0,0,True,2024-01,2026-06,1971-04,2026-07,CRMLSListing_Residential_202401_202606_Mortgage_Enriched.csv
