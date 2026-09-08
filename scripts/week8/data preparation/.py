"""Prepare analysis-ready Week 8 data sources for Tableau.

The Week 8 Tableau foundation uses two separate event-grain data sources:

1. Residential sold transactions for close-date market and competition metrics.
2. Residential listings for listing-date new-listing metrics.

The sources remain separate so a join cannot multiply records or distort sums,
averages, medians, and counts.  The script also creates a monthly reconciliation
table and a compact QA summary that can be used to verify Tableau worksheets.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "week8_tableau_foundation"

SOLD_INPUT = (
    PROJECT_ROOT
    / "outputs"
    / "week7_outlier_detection"
    / "CRMLSSold_Residential_202401_202606_Week7_Clean_Filtered.csv"
)
LISTING_INPUT = (
    PROJECT_ROOT
    / "outputs"
    / "week4_5_data_cleaning"
    / "CRMLSListing_Residential_202401_202606_Week5_Cleaned.csv"
)

SOLD_OUTPUT = (
    OUTPUT_DIR / "CRMLSSold_Residential_202401_202606_Week8_Tableau_Ready.csv"
)
LISTING_OUTPUT = (
    OUTPUT_DIR / "CRMLSListing_Residential_202401_202606_Week8_Tableau_Ready.csv"
)
MONTHLY_METRICS_OUTPUT = OUTPUT_DIR / "week8_monthly_market_metrics.csv"
QA_SUMMARY_OUTPUT = OUTPUT_DIR / "week8_tableau_qa_summary.csv"
FIELD_DICTIONARY_OUTPUT = OUTPUT_DIR / "week8_tableau_field_dictionary.csv"

KEY_COLUMN = "ListingKey"
START_DATE = pd.Timestamp("2024-01-01")
RATIO_LOWER_BOUND = 0.50
RATIO_UPPER_BOUND = 2.00

SOLD_COLUMNS = [
    KEY_COLUMN,
    "CloseDate",
    "ClosePrice",
    "OriginalListPrice",
    "ListPrice",
    "DaysOnMarket",
    "LivingArea",
    "price_per_sqft",
    "close_to_original_list_ratio",
    "City",
    "CountyOrParish",
    "PostalCode",
    "PropertyType",
    "PropertySubType",
    "StateOrProvince",
    "ListAgentFullName",
    "ListOfficeName",
    "Latitude",
    "Longitude",
    "rate_30yr_fixed",
]

LISTING_COLUMNS = [
    KEY_COLUMN,
    "ListingContractDate",
    "City",
    "CountyOrParish",
    "PostalCode",
    "PropertyType",
    "PropertySubType",
    "StateOrProvince",
    "ListAgentFullName",
    "ListOfficeName",
    "MlsStatus",
]


def require_columns(path: Path, required: list[str]) -> None:
    """Fail early when an input file or a required field is unavailable."""
    if not path.exists():
        raise FileNotFoundError(path)
    available = set(pd.read_csv(path, nrows=0).columns)
    missing = sorted(set(required).difference(available))
    if missing:
        raise ValueError(f"{path.name} is missing columns: {', '.join(missing)}")


def normalize_postal_code(series: pd.Series) -> pd.Series:
    """Preserve postal codes as five-character Tableau geographic dimensions."""
    values = series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    digit_mask = values.str.fullmatch(r"\d{1,5}", na=False)
    values.loc[digit_mask] = values.loc[digit_mask].str.zfill(5)
    return values


def load_sold_source() -> pd.DataFrame:
    """Load the Week 7 clean sold source and add Tableau helper fields."""
    require_columns(SOLD_INPUT, SOLD_COLUMNS)
    sold = pd.read_csv(
        SOLD_INPUT,
        usecols=SOLD_COLUMNS,
        dtype={KEY_COLUMN: "string", "PostalCode": "string"},
        low_memory=False,
    )
    sold["CloseDate"] = pd.to_datetime(sold["CloseDate"], errors="coerce")
    if sold[KEY_COLUMN].isna().any() or sold["CloseDate"].isna().any():
        raise ValueError("Sold source contains a missing ListingKey or CloseDate")
    if sold[KEY_COLUMN].duplicated(keep=False).any():
        raise ValueError("Week 7 clean sold source is not unique by ListingKey")
    if sold["CloseDate"].min() < START_DATE:
        raise ValueError("Sold source contains a CloseDate before 2024-01-01")

    sold["PostalCode"] = normalize_postal_code(sold["PostalCode"])
    sold["CloseMonth"] = sold["CloseDate"].dt.to_period("M").dt.to_timestamp()

    ratio = pd.to_numeric(sold["close_to_original_list_ratio"], errors="coerce")
    sold["CloseToOriginalRatioValidFlag"] = ratio.between(
        RATIO_LOWER_BOUND,
        RATIO_UPPER_BOUND,
        inclusive="both",
    )
    sold["ValidCloseToOriginalListRatio"] = ratio.where(
        sold["CloseToOriginalRatioValidFlag"]
    )
    return sold


def load_listing_source() -> tuple[pd.DataFrame, int]:
    """Load listings, keep the newest snapshot, and add a listing-month field."""
    require_columns(LISTING_INPUT, LISTING_COLUMNS)
    listings = pd.read_csv(
        LISTING_INPUT,
        usecols=LISTING_COLUMNS,
        dtype={KEY_COLUMN: "string", "PostalCode": "string"},
        low_memory=False,
    )
    listings["ListingContractDate"] = pd.to_datetime(
        listings["ListingContractDate"], errors="coerce"
    )
    if listings[KEY_COLUMN].isna().any() or listings["ListingContractDate"].isna().any():
        raise ValueError("Listing source contains a missing ListingKey or ListingContractDate")
    if listings["ListingContractDate"].min() < START_DATE:
        raise ValueError("Listing source contains a ListingContractDate before 2024-01-01")

    duplicate_snapshots = int(listings[KEY_COLUMN].duplicated(keep="last").sum())
    listings = listings.drop_duplicates(KEY_COLUMN, keep="last").copy()
    listings["PostalCode"] = normalize_postal_code(listings["PostalCode"])
    listings["ListingMonth"] = (
        listings["ListingContractDate"].dt.to_period("M").dt.to_timestamp()
    )
    return listings, duplicate_snapshots


def build_monthly_metrics(
    sold: pd.DataFrame,
    listings: pd.DataFrame,
) -> pd.DataFrame:
    """Create monthly control totals for the five required market metrics."""
    sold_monthly = (
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
    listing_monthly = (
        listings.groupby("ListingMonth", as_index=False)
        .agg(NewListings=(KEY_COLUMN, "nunique"))
        .rename(columns={"ListingMonth": "Month"})
    )
    monthly = sold_monthly.merge(listing_monthly, on="Month", how="outer")
    monthly = monthly.sort_values("Month", kind="stable").reset_index(drop=True)
    return monthly[
        [
            "Month",
            "MonthlyMedianClosePrice",
            "AverageDaysOnMarket",
            "AverageCloseToOriginalListRatio",
            "NewListings",
            "ClosedSales",
            "TotalSalesVolume",
        ]
    ]


def build_qa_summary(
    sold: pd.DataFrame,
    listings: pd.DataFrame,
    duplicate_listing_snapshots: int,
) -> pd.DataFrame:
    """Create compact expected values for Tableau reconciliation."""
    valid_ratio = sold["ValidCloseToOriginalListRatio"]
    raw_ratio = pd.to_numeric(
        sold["close_to_original_list_ratio"], errors="coerce"
    )
    rows = [
        ("sold_rows", len(sold), "rows", "Sold_Clean"),
        ("sold_unique_listing_keys", sold[KEY_COLUMN].nunique(), "listings", "Sold_Clean"),
        ("sold_min_close_date", sold["CloseDate"].min().date(), "date", "Sold_Clean"),
        ("sold_max_close_date", sold["CloseDate"].max().date(), "date", "Sold_Clean"),
        ("overall_median_close_price", sold["ClosePrice"].median(), "USD", "Sold_Clean"),
        ("overall_average_days_on_market", sold["DaysOnMarket"].mean(), "days", "Sold_Clean"),
        ("overall_total_sales_volume", sold["ClosePrice"].sum(), "USD", "Sold_Clean"),
        ("raw_ratio_non_null_rows", raw_ratio.notna().sum(), "rows", "Sold_Clean"),
        (
            "valid_ratio_rows",
            valid_ratio.notna().sum(),
            "rows",
            "Sold_Clean",
        ),
        (
            "ratio_rows_excluded_by_0_5_to_2_0_rule",
            int(raw_ratio.notna().sum() - valid_ratio.notna().sum()),
            "rows",
            "Sold_Clean",
        ),
        (
            "overall_average_valid_close_to_original_ratio",
            valid_ratio.mean(),
            "ratio",
            "Sold_Clean",
        ),
        ("listing_rows_after_deduplication", len(listings), "rows", "Listings_Clean"),
        (
            "listing_unique_listing_keys",
            listings[KEY_COLUMN].nunique(),
            "listings",
            "Listings_Clean",
        ),
        (
            "listing_duplicate_snapshots_removed",
            duplicate_listing_snapshots,
            "rows",
            "Listings_Clean",
        ),
        (
            "listing_min_contract_date",
            listings["ListingContractDate"].min().date(),
            "date",
            "Listings_Clean",
        ),
        (
            "listing_max_contract_date",
            listings["ListingContractDate"].max().date(),
            "date",
            "Listings_Clean",
        ),
    ]
    return pd.DataFrame(rows, columns=["metric", "expected_value", "unit", "data_source"])


def build_field_dictionary() -> pd.DataFrame:
    """Document the core Tableau roles and metric usage."""
    rows = [
        ("Sold_Clean", "ListingKey", "String / Dimension", "Unique sold transaction; use COUNTD for units"),
        ("Sold_Clean", "CloseDate", "Date", "Transaction close date"),
        ("Sold_Clean", "CloseMonth", "Date", "First day of close month; use as continuous month"),
        ("Sold_Clean", "ClosePrice", "Number / Measure", "Median price and total sales volume"),
        ("Sold_Clean", "DaysOnMarket", "Number / Measure", "Average days on market"),
        ("Sold_Clean", "ValidCloseToOriginalListRatio", "Number / Measure", "Average; format as percentage"),
        ("Sold_Clean", "CloseToOriginalRatioValidFlag", "Boolean", "True for ratios from 0.50 through 2.00"),
        ("Sold_Clean", "ListAgentFullName", "String / Dimension", "Listing-agent rankings"),
        ("Sold_Clean", "ListOfficeName", "String / Dimension", "Listing-office rankings"),
        ("Sold_Clean", "PostalCode", "String / ZIP Code", "ZIP map and geographic filter"),
        ("Sold_Clean", "City", "String / Dimension", "Global geographic filter"),
        ("Sold_Clean", "CountyOrParish", "String / Dimension", "Global geographic filter"),
        ("Sold_Clean", "PropertySubType", "String / Dimension", "Required property-subtype filter"),
        ("Listings_Clean", "ListingKey", "String / Dimension", "Unique listing; use COUNTD for new listings"),
        ("Listings_Clean", "ListingContractDate", "Date", "Date the listing entered the market"),
        ("Listings_Clean", "ListingMonth", "Date", "First day of listing month; use as continuous month"),
        ("Listings_Clean", "PostalCode", "String / ZIP Code", "Required ZIP filter"),
        ("Listings_Clean", "City", "String / Dimension", "Required city filter"),
        ("Listings_Clean", "CountyOrParish", "String / Dimension", "Required county filter"),
        ("Listings_Clean", "PropertySubType", "String / Dimension", "Required property-subtype filter"),
    ]
    return pd.DataFrame(rows, columns=["data_source", "field", "tableau_role", "usage"])


def write_csv(data: pd.DataFrame, path: Path) -> None:
    """Write deterministic Tableau inputs with ISO date formatting."""
    data.to_csv(path, index=False, date_format="%Y-%m-%d")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sold = load_sold_source()
    listings, duplicate_listing_snapshots = load_listing_source()
    monthly = build_monthly_metrics(sold, listings)
    qa_summary = build_qa_summary(sold, listings, duplicate_listing_snapshots)
    field_dictionary = build_field_dictionary()

    write_csv(sold, SOLD_OUTPUT)
    write_csv(listings, LISTING_OUTPUT)
    write_csv(monthly, MONTHLY_METRICS_OUTPUT)
    write_csv(qa_summary, QA_SUMMARY_OUTPUT)
    write_csv(field_dictionary, FIELD_DICTIONARY_OUTPUT)

    print(f"Sold Tableau rows: {len(sold):,}")
    print(f"Listing Tableau rows: {len(listings):,}")
    print(f"Listing duplicate snapshots removed: {duplicate_listing_snapshots:,}")
    print(f"Monthly control rows: {len(monthly):,}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
