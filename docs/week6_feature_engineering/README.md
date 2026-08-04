# Week 6 - Feature Engineering and Market Metrics

## Overview

This folder contains the Week 6 feature-engineering and segmented-market-analysis work for the IDX Exchange internship project. The analysis uses the cleaned residential sold dataset produced in Weeks 4-5.

The workflow has two stages:

1. Create analysis-ready housing market metrics from raw MLS fields.
2. Summarize those metrics by property subtype, county, listing office, and buyer office.

## Workflow

```text
Week 5 cleaned sold data
        |
        v
week6_feature_engineering.py
        |
        +-- Complete engineered dataset (local only)
        +-- 25-row engineered sample
        |
        v
week6_segment_analysis.py
        |
        +-- Property subtype summary
        +-- County summary
        +-- Listing office summary and Top 100
        +-- Buyer office summary and Top 100
```

## Engineered Metrics

| Metric | Formula or source | Purpose |
|---|---|---|
| `price_ratio` | `ClosePrice / ListPrice` | Measures the relationship between the sale price and final list price |
| `close_to_original_list_ratio` | `ClosePrice / OriginalListPrice` | Captures the full pricing and reduction history |
| `price_per_sqft` | `ClosePrice / LivingArea` | Normalizes prices across different property sizes |
| `days_on_market` | `DaysOnMarket` | Measures time on market |
| `year` | Derived from `CloseDate` | Supports annual analysis |
| `month` | Derived from `CloseDate` | Supports monthly analysis |
| `YrMo` | `YYYY-MM` derived from `CloseDate` | Supports monthly time-series analysis |
| `listing_to_contract_days` | `PurchaseContractDate - ListingContractDate` | Measures time from listing to accepted offer |
| `contract_to_close_days` | `CloseDate - PurchaseContractDate` | Measures the escrow and closing period |

Ratios are calculated only when both inputs are present and positive. Invalid divisions return missing values instead of infinity. Negative transaction-duration values are retained and flagged rather than deleted.

## Segment Analysis

The same reusable aggregation function produces summaries for:

- `PropertySubType`
- `CountyOrParish`
- `ListOfficeName`
- `BuyerOfficeName`

`PropertyType` is not included because the dataset was previously filtered to Residential, leaving only one category. `MLSAreaMajor` is outside the selected scope because of its high cardinality and substantial missing/undefined share; county is used as the primary geographic segment.

Each segment summary includes:

- Unique transaction count
- Total sales volume
- Median close price
- Median price per square foot
- Average and median days on market
- Average final-list-price ratio
- Average original-list-price ratio
- Average listing-to-contract days
- Average contract-to-close days
- Transaction and sales-volume market share
- Transaction-count and sales-volume ranks

The Office Top 100 tables are ranked by total sales volume. Missing, placeholder, and `NONMEMBER` office labels remain in the complete summaries but are excluded from Top 100 rankings.

## Files for GitHub Submission

### Scripts

| File | Description |
|---|---|
| `week6_feature_engineering.py` | Creates all Week 6 engineered metrics and sample output |
| `week6_segment_analysis.py` | Generates the four selected segment summaries and Office Top 100 tables |

### Small output files

| File | Description |
|---|---|
| `week6_engineered_sample.csv` | Twenty-five complete sample records with source and engineered fields |
| `week6_feature_engineering_validation.csv` | Row-count, missing-value, infinity, and negative-value checks |
| `week6_summary_by_property_subtype.csv` | Property-subtype market summary |
| `week6_summary_by_county.csv` | County market summary |
| `week6_summary_by_list_office.csv` | Complete listing-office summary |
| `week6_summary_by_buyer_office.csv` | Complete buyer-office summary |
| `week6_top100_list_offices.csv` | Top 100 listing offices by sales volume |
| `week6_top100_buyer_offices.csv` | Top 100 buyer offices by sales volume |

### Local-only large output

`CRMLSSold_Residential_202401_202606_Week6_Engineered.csv` is approximately 337 MB and is intentionally excluded by the repository `.gitignore`. It should remain local and should not be uploaded directly to GitHub.

### Overall Output

| Measure | Result |
|---|---:|
| Analysis period | January 2024 - June 2026 |
| Cleaned sold records processed | 447,771 |
| Unique transactions used in segment analysis | 447,395 |
| Repeated transaction snapshots excluded | 376 |
| Estimated total sales volume | $533.39 billion |
| Engineered variables created | 9 |
| Property subtype groups | 21 |
| County groups | 63 |
| Listing office groups | 19,155 |
| Buyer office groups | 21,868 |


## Data Handling and QA

- Feature engineering preserves all 447,771 cleaned source rows.
- The segment analysis resolves repeated transaction snapshots by retaining the last occurrence of each `ListingKey`.
- Segment summaries analyze 447,395 unique transactions after excluding 376 repeated snapshots.
- Negative transaction durations do not contribute to duration averages.
- All engineered formula groups passed independent recomputation.
- No engineered numeric field contains infinite values.
- Segment transaction totals reconcile to 447,395 unique transactions.
- Market-share columns reconcile to approximately 100%, subject only to displayed decimal precision.

## Week 6 Skills Practiced

- Feature engineering from raw fields
- Housing market metric interpretation
- Time-series variable construction
- Segmented market analysis
- Competitive intelligence using sales volume and transaction counts
- Data-quality checks for missing values, invalid ratios, duplicate transactions, and inconsistent dates

---


