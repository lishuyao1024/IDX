"""Independently validate the Week 8 Tableau foundation outputs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
SOLD_FILE = BASE_DIR / "CRMLSSold_Residential_202401_202606_Week8_Tableau_Ready.csv"
LISTING_FILE = BASE_DIR / "CRMLSListing_Residential_202401_202606_Week8_Tableau_Ready.csv"
MONTHLY_FILE = BASE_DIR / "week8_monthly_market_metrics.csv"
QA_FILE = BASE_DIR / "week8_tableau_qa_summary.csv"
DICTIONARY_FILE = BASE_DIR / "week8_tableau_field_dictionary.csv"
KEY_COLUMN = "ListingKey"


def assert_close(actual: float, expected: float, label: str) -> None:
    if not np.isclose(actual, expected, rtol=1e-9, atol=1e-6, equal_nan=True):
        raise AssertionError(f"{label}: actual={actual}, expected={expected}")


def main() -> None:
    for path in [SOLD_FILE, LISTING_FILE, MONTHLY_FILE, QA_FILE, DICTIONARY_FILE]:
        if not path.exists():
            raise FileNotFoundError(path)

    sold = pd.read_csv(
        SOLD_FILE,
        dtype={KEY_COLUMN: "string", "PostalCode": "string"},
        parse_dates=["CloseDate", "CloseMonth"],
        low_memory=False,
    )
    listings = pd.read_csv(
        LISTING_FILE,
        dtype={KEY_COLUMN: "string", "PostalCode": "string"},
        parse_dates=["ListingContractDate", "ListingMonth"],
        low_memory=False,
    )
    monthly = pd.read_csv(MONTHLY_FILE, parse_dates=["Month"])
    qa = pd.read_csv(QA_FILE, dtype={"expected_value": "string"}).set_index("metric")

    if len(sold) != 376_529 or sold[KEY_COLUMN].nunique() != 376_529:
        raise AssertionError("Sold Tableau grain does not reconcile to Week 7")
    if sold[KEY_COLUMN].duplicated(keep=False).any():
        raise AssertionError("Sold Tableau output is not unique by ListingKey")
    if len(listings) != 615_484 or listings[KEY_COLUMN].nunique() != 615_484:
        raise AssertionError("Listing Tableau grain does not reconcile to Week 5")
    if listings[KEY_COLUMN].duplicated(keep=False).any():
        raise AssertionError("Listing Tableau output is not unique by ListingKey")
    if set(sold["PropertyType"].dropna().unique()) != {"Residential"}:
        raise AssertionError("Sold Tableau output is not Residential-only")
    if set(listings["PropertyType"].dropna().unique()) != {"Residential"}:
        raise AssertionError("Listing Tableau output is not Residential-only")

    if not sold["CloseMonth"].equals(
        sold["CloseDate"].dt.to_period("M").dt.to_timestamp()
    ):
        raise AssertionError("CloseMonth does not match CloseDate")
    if not listings["ListingMonth"].equals(
        listings["ListingContractDate"].dt.to_period("M").dt.to_timestamp()
    ):
        raise AssertionError("ListingMonth does not match ListingContractDate")

    valid_ratio = sold["ValidCloseToOriginalListRatio"]
    if not valid_ratio.dropna().between(0.5, 2.0, inclusive="both").all():
        raise AssertionError("Valid ratio contains a value outside 0.50-2.00")
    expected_valid_flag = sold["close_to_original_list_ratio"].between(
        0.5, 2.0, inclusive="both"
    )
    actual_valid_flag = sold["CloseToOriginalRatioValidFlag"].astype(bool)
    if not actual_valid_flag.equals(expected_valid_flag):
        raise AssertionError("Ratio validity flag does not recompute")
    expected_valid_ratio = sold["close_to_original_list_ratio"].where(
        expected_valid_flag
    )
    if not np.allclose(
        valid_ratio.to_numpy(dtype="float64", na_value=np.nan),
        expected_valid_ratio.to_numpy(dtype="float64", na_value=np.nan),
        equal_nan=True,
    ):
        raise AssertionError("Valid ratio values do not recompute")

    sold_expected = (
        sold.groupby("CloseMonth", as_index=False)
        .agg(
            MonthlyMedianClosePrice=("ClosePrice", "median"),
            AverageDaysOnMarket=("DaysOnMarket", "mean"),
            AverageCloseToOriginalListRatio=(
                "ValidCloseToOriginalListRatio",
                "mean",
            ),
            ClosedSales=(KEY_COLUMN, "nunique"),
            TotalSalesVolume=("ClosePrice", "sum"),
        )
        .rename(columns={"CloseMonth": "Month"})
    )
    listing_expected = (
        listings.groupby("ListingMonth", as_index=False)
        .agg(NewListings=(KEY_COLUMN, "nunique"))
        .rename(columns={"ListingMonth": "Month"})
    )
    expected_monthly = sold_expected.merge(listing_expected, on="Month", how="outer")
    expected_monthly = expected_monthly.sort_values("Month").reset_index(drop=True)
    monthly = monthly.sort_values("Month").reset_index(drop=True)

    if not monthly["Month"].equals(expected_monthly["Month"]):
        raise AssertionError("Monthly control dates do not recompute")
    for column in [
        "MonthlyMedianClosePrice",
        "AverageDaysOnMarket",
        "AverageCloseToOriginalListRatio",
        "NewListings",
        "ClosedSales",
        "TotalSalesVolume",
    ]:
        if not np.allclose(
            monthly[column].to_numpy(dtype="float64", na_value=np.nan),
            expected_monthly[column].to_numpy(dtype="float64", na_value=np.nan),
            rtol=1e-9,
            atol=1e-6,
            equal_nan=True,
        ):
            raise AssertionError(f"Monthly metric does not recompute: {column}")

    qa_checks = {
        "sold_rows": len(sold),
        "sold_unique_listing_keys": sold[KEY_COLUMN].nunique(),
        "overall_median_close_price": sold["ClosePrice"].median(),
        "overall_average_days_on_market": sold["DaysOnMarket"].mean(),
        "overall_total_sales_volume": sold["ClosePrice"].sum(),
        "valid_ratio_rows": valid_ratio.notna().sum(),
        "overall_average_valid_close_to_original_ratio": valid_ratio.mean(),
        "listing_rows_after_deduplication": len(listings),
        "listing_unique_listing_keys": listings[KEY_COLUMN].nunique(),
    }
    for metric, actual in qa_checks.items():
        expected = float(qa.loc[metric, "expected_value"])
        assert_close(float(actual), expected, metric)

    if sold["CloseDate"].min() != pd.Timestamp("2024-01-01"):
        raise AssertionError("Unexpected minimum CloseDate")
    if sold["CloseDate"].max() != pd.Timestamp("2026-06-30"):
        raise AssertionError("Unexpected maximum CloseDate")
    if listings["ListingContractDate"].min() != pd.Timestamp("2024-01-01"):
        raise AssertionError("Unexpected minimum ListingContractDate")
    if listings["ListingContractDate"].max() != pd.Timestamp("2026-06-30"):
        raise AssertionError("Unexpected maximum ListingContractDate")

    print("Week 8 Tableau foundation validation passed.")
    print(f"Sold transactions: {len(sold):,}")
    print(f"Unique listings: {len(listings):,}")
    print(f"Monthly periods: {len(monthly):,}")
    print(f"Valid ratio average: {valid_ratio.mean():.6f}")


if __name__ == "__main__":
    main()
