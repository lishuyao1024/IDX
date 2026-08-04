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

## Week 6 Results Summary

Week 6 processed 447,771 cleaned residential sold records and created nine market and time-series variables. After excluding 376 repeated transaction snapshots, the segment analysis used 447,395 unique transactions with approximately $533.39 billion in total sales volume.

### Feature Engineering

The following variables were created:

- `price_ratio`
- `close_to_original_list_ratio`
- `price_per_sqft`
- `days_on_market`
- `year`, `month`, and `YrMo`
- `listing_to_contract_days`
- `contract_to_close_days`

No engineered numeric field contained infinite values. Negative transaction durations were flagged and excluded from duration averages without deleting the transactions.

### Property Subtype Results

| Rank | Property subtype | Transactions | Share | Median price | Median price/sq. ft. |
|---:|---|---:|---:|---:|---:|
| 1 | Single Family Residence | 335,138 | 74.91% | $897,500 | $533.33 |
| 2 | Condominium | 73,531 | 16.44% | $627,000 | $564.17 |
| 3 | Townhouse | 26,228 | 5.86% | $800,000 | $560.90 |

The three largest property subtypes represented 97.21% of all transactions. Single-family residences led in transaction count and total sales volume, while condominiums had the highest median price per square foot among the major subtypes.

### County Results

| Measure | First | Second | Third |
|---|---|---|---|
| Transactions | Los Angeles | Riverside | San Diego |
| Total sales volume | Los Angeles | San Diego | Orange |
| Median close price | San Mateo | Santa Clara | Orange |
| Median price/sq. ft. | San Mateo | Santa Clara | Alameda |
| Fastest average DOM | Santa Clara | Alameda | San Mateo |

Key county results:

- Los Angeles recorded 110,975 transactions and $147.03 billion in sales volume.
- San Mateo had the highest major-county median price at $1.70 million.
- San Mateo also had the highest median price per square foot at $1,052.63.
- Santa Clara had the shortest average DOM at 21.95 days.
- Riverside had the longest average DOM among the major counties at 48.51 days.

Price and DOM rankings include counties with at least 5,000 transactions.

### Listing Office Top 3

| Rank | Listing office | Transactions | Sales volume |
|---:|---|---:|---:|
| 1 | Compass | 31,705 | $58.73B |
| 2 | Coldwell Banker Realty | 20,191 | $33.55B |
| 3 | Keller Williams Realty | 8,754 | $9.05B |

The Top 100 listing offices represented 52.87% of total sales volume and 40.88% of transactions.

### Buyer Office Top 3

| Rank | Buyer office | Transactions | Sales volume |
|---:|---|---:|---:|
| 1 | Compass | 29,594 | $53.96B |
| 2 | Coldwell Banker Realty | 16,222 | $27.79B |
| 3 | Keller Williams Realty | 6,899 | $8.62B |

The Top 100 buyer offices represented 51.76% of total sales volume and 42.07% of transactions. Missing and `NONMEMBER` office labels were retained in the complete summary but excluded from the Top 100 ranking.

### Main Takeaways

- Single-family residences dominated the market.
- Los Angeles was the largest county by transactions and sales volume.
- San Mateo was the highest-priced major county.
- Santa Clara had the fastest major-county market.
- Compass ranked first on both the listing and buyer sides.

> **Note:** These are preliminary Week 6 descriptive results. Week 7 outlier detection has not yet been applied, so extreme records may still affect averages and total sales volume.


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


