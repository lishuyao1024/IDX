"""Answer the Weeks 2-3 foundational EDA questions (excluding mortgage rates)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def date_column(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_datetime(frame[column], errors="coerce")


def distribution_row(name: str, series: pd.Series) -> dict:
    valid = numeric(series).dropna()
    quantiles = valid.quantile([0.01, 0.25, 0.50, 0.75, 0.99])
    return {
        "metric": name,
        "valid_count": int(valid.size),
        "missing_or_non_numeric": int(len(series) - valid.size),
        "minimum": float(valid.min()),
        "p01": float(quantiles.loc[0.01]),
        "p25": float(quantiles.loc[0.25]),
        "mean": float(valid.mean()),
        "median": float(quantiles.loc[0.50]),
        "p75": float(quantiles.loc[0.75]),
        "p99": float(quantiles.loc[0.99]),
        "maximum": float(valid.max()),
        "zero_or_negative_count": int((valid <= 0).sum()),
    }


def analyze(input_dir: Path, row_summary_path: Path) -> dict:
    sold_path = input_dir / "CRMLSSold_Residential_202401_202605.csv"
    listing_path = input_dir / "CRMLSListing_Residential_202401_202605.csv"

    sold_columns = [
        "ClosePrice",
        "ListPrice",
        "DaysOnMarket",
        "CloseDate",
        "PurchaseContractDate",
        "ListingContractDate",
        "CountyOrParish",
    ]
    listing_columns = ["ListPrice", "DaysOnMarket"]
    sold = pd.read_csv(sold_path, usecols=sold_columns, low_memory=False)
    listing = pd.read_csv(listing_path, usecols=listing_columns, low_memory=False)

    # Residential share is calculated from Week 1's pre-filter and post-filter
    # counts so the denominator includes every original property type.
    row_summary = pd.read_csv(row_summary_path)
    residential_share = []
    for row in row_summary.to_dict("records"):
        total = int(row["rows_before_residential_filter"])
        residential = int(row["rows_after_residential_filter"])
        residential_share.append(
            {
                "dataset": row["dataset"],
                "all_property_types": total,
                "residential": residential,
                "other_property_types": total - residential,
                "residential_percentage": residential / total,
                "other_percentage": (total - residential) / total,
            }
        )

    distributions = [
        distribution_row("Sold ClosePrice", sold["ClosePrice"]),
        distribution_row("Sold DaysOnMarket", sold["DaysOnMarket"]),
        distribution_row("Listing ListPrice", listing["ListPrice"]),
        distribution_row("Listing DaysOnMarket", listing["DaysOnMarket"]),
    ]

    close_price = numeric(sold["ClosePrice"])
    list_price = numeric(sold["ListPrice"])
    comparable = close_price.notna() & list_price.notna() & (list_price > 0)
    relationship = pd.Series(
        np.select(
            [
                close_price[comparable] > list_price[comparable],
                close_price[comparable] < list_price[comparable],
            ],
            ["Above list price", "Below list price"],
            default="At list price",
        ),
        index=sold.index[comparable],
    )
    relationship_counts = relationship.value_counts()
    comparable_count = int(comparable.sum())
    sale_vs_list = []
    for label in ["Above list price", "At list price", "Below list price"]:
        count = int(relationship_counts.get(label, 0))
        sale_vs_list.append(
            {
                "result": label,
                "sold_count": count,
                "percentage_of_comparable_sales": count / comparable_count,
            }
        )
    sale_vs_list.append(
        {
            "result": "Not comparable (missing/nonpositive price)",
            "sold_count": int(len(sold) - comparable_count),
            "percentage_of_comparable_sales": None,
        }
    )

    listing_date = date_column(sold, "ListingContractDate")
    purchase_date = date_column(sold, "PurchaseContractDate")
    close_date = date_column(sold, "CloseDate")
    date_checks = [
        {
            "check": "Listing date after close date",
            "eligible_rows": int((listing_date.notna() & close_date.notna()).sum()),
            "flagged_rows": int((listing_date > close_date).sum()),
        },
        {
            "check": "Purchase contract date after close date",
            "eligible_rows": int((purchase_date.notna() & close_date.notna()).sum()),
            "flagged_rows": int((purchase_date > close_date).sum()),
        },
        {
            "check": "Listing date after purchase contract date",
            "eligible_rows": int((listing_date.notna() & purchase_date.notna()).sum()),
            "flagged_rows": int((listing_date > purchase_date).sum()),
        },
    ]
    for row in date_checks:
        row["flagged_percentage"] = (
            row["flagged_rows"] / row["eligible_rows"]
            if row["eligible_rows"]
            else None
        )

    county_frame = pd.DataFrame(
        {
            "county": sold["CountyOrParish"].astype("string").str.strip(),
            "close_price": close_price,
        }
    ).dropna()
    county_frame = county_frame.loc[
        county_frame["county"].ne("") & county_frame["close_price"].gt(0)
    ]
    county_summary = (
        county_frame.groupby("county", as_index=False)["close_price"]
        .agg(transaction_count="count", median_close_price="median", mean_close_price="mean")
    )
    county_summary = county_summary.loc[county_summary["transaction_count"] >= 100]
    county_summary = county_summary.sort_values(
        ["median_close_price", "transaction_count"], ascending=[False, False]
    ).head(10)
    county_summary.insert(0, "rank", range(1, len(county_summary) + 1))

    conclusions = [
        {
            "question": "What is the Residential vs. other property type share?",
            "conclusion": "; ".join(
                f"{row['dataset']}: Residential {row['residential_percentage']:.1%}, "
                f"other {row['other_percentage']:.1%}"
                for row in residential_share
            ),
        },
        {
            "question": "What are the median and average close prices?",
            "conclusion": (
                f"Sold ClosePrice median is ${distributions[0]['median']:,.0f}; "
                f"mean is ${distributions[0]['mean']:,.0f}, indicating a right-skewed distribution."
            ),
        },
        {
            "question": "What does the Days on Market distribution look like?",
            "conclusion": (
                f"Sold DOM median is {distributions[1]['median']:.0f} days and mean is "
                f"{distributions[1]['mean']:.1f}; Listing DOM median is "
                f"{distributions[3]['median']:.0f} and mean is {distributions[3]['mean']:.1f}. "
                "Both distributions are right-skewed."
            ),
        },
        {
            "question": "What percentage of homes sold above vs. below list price?",
            "conclusion": "; ".join(
                f"{row['result']}: {row['percentage_of_comparable_sales']:.1%}"
                for row in sale_vs_list[:3]
            ),
        },
        {
            "question": "Are there apparent date consistency issues?",
            "conclusion": "; ".join(
                f"{row['check']}: {row['flagged_rows']:,} "
                f"({row['flagged_percentage']:.2%} of eligible)"
                for row in date_checks
            ),
        },
        {
            "question": "Which counties have the highest median prices?",
            "conclusion": (
                "Among counties with at least 100 valid positive-price sales, the top three are "
                + ", ".join(
                    f"{row.county} (${row.median_close_price:,.0f})"
                    for row in county_summary.head(3).itertuples()
                )
                + "."
            ),
        },
    ]

    return {
        "coverage": {
            "period": "2024-01 through 2026-05",
            "sold_residential_rows": int(len(sold)),
            "listing_residential_rows": int(len(listing)),
            "notes": (
                "Exploratory results use the Residential-filtered Week 1 datasets. "
                "Numeric values are converted with invalid text treated as missing. "
                "County ranking requires at least 100 valid positive-price sales."
            ),
        },
        "conclusions": conclusions,
        "residential_share": residential_share,
        "distributions": distributions,
        "sale_vs_list": sale_vs_list,
        "date_checks": date_checks,
        "county_median_top10": county_summary.to_dict("records"),
    }


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir.parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=workspace / "outputs" / "week1")
    parser.add_argument(
        "--row-summary",
        type=Path,
        default=workspace
        / "outputs"
        / "week1"
        / "week1_row_count_summary_202401_202605.csv",
    )
    parser.add_argument("--output-json", type=Path, default=script_dir / "basic_eda_results.json")
    args = parser.parse_args()

    report = analyze(args.input_dir, args.row_summary)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    print(f"EDA results saved to {args.output_json}")


if __name__ == "__main__":
    main()
