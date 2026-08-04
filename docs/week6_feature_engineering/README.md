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

## Detailed Results and Rankings

### 1. Feature Engineering Completion

Source file represented by: [week6_engineered_sample.csv](./week6_engineered_sample.csv)

A total of 447,771 cleaned residential sold records were processed. The following table shows how many records received each engineered variable.

| Engineered variable | Populated records | Missing records | Infinite values | Negative values |
|---|---:|---:|---:|---:|
| `price_ratio` | 447,771 | 0 | 0 | 0 |
| `close_to_original_list_ratio` | 446,948 | 823 | 0 | 0 |
| `price_per_sqft` | 447,518 | 253 | 0 | 0 |
| `days_on_market` | 447,771 | 0 | 0 | 0 |
| `year` | 447,771 | 0 | 0 | 0 |
| `month` | 447,771 | 0 | 0 | 0 |
| `YrMo` | 447,771 | 0 | 0 | Not applicable |
| `listing_to_contract_days` | 447,573 | 198 | 0 | 289 |
| `contract_to_close_days` | 447,574 | 197 | 0 | 239 |

#### Feature-engineering conclusions

- `price_ratio`, `days_on_market`, `year`, `month`, and `YrMo` were successfully populated for all 447,771 records.
- No engineered numeric variable contained infinite values.
- A total of 823 records could not receive `close_to_original_list_ratio`, primarily because the required original list price was unavailable or invalid.
- A total of 253 records could not receive `price_per_sqft`, primarily because the required living-area value was unavailable or invalid.
- There were 289 negative listing-to-contract durations.
- There were 239 negative contract-to-close durations.
- Negative transaction durations were flagged and retained in the full dataset but excluded from segment-level duration averages.
- The 25-row sample contains all original calculation fields and all nine engineered variables.
- The sample covers closing dates from January 2 through January 31, 2024, and is intended for calculation review rather than market representation.

---

## 2. Property Subtype Rankings

Source file: [week6_summary_by_property_subtype.csv](./week6_summary_by_property_subtype.csv)

The property-subtype summary contains 21 groups and reconciles to 447,395 unique transactions.

### Top 3 property subtypes by transaction count

| Rank | Property subtype | Transactions | Transaction share |
|---:|---|---:|---:|
| 1 | Single Family Residence | 335,138 | 74.91% |
| 2 | Condominium | 73,531 | 16.44% |
| 3 | Townhouse | 26,228 | 5.86% |

These three property subtypes accounted for approximately 97.21% of all unique transactions.

### Top 3 property subtypes by total sales volume

| Rank | Property subtype | Total sales volume | Transactions |
|---:|---|---:|---:|
| 1 | Single Family Residence | $434.65B | 335,138 |
| 2 | Condominium | $64.43B | 73,531 |
| 3 | Townhouse | $26.47B | 26,228 |

Single-family residences represented approximately 81.49% of the total $533.39 billion sales volume.

### Highest median close prices

The following ranking includes property subtypes with at least 100 transactions.

| Rank | Property subtype | Median close price | Transactions |
|---:|---|---:|---:|
| 1 | Quadruplex | $1,262,750 | 158 |
| 2 | Triplex | $1,135,000 | 373 |
| 3 | Duplex | $910,000 | 2,480 |

Quadruplex and Triplex had high median prices, but their transaction counts were much smaller than those of the three major residential segments. Their results should therefore be interpreted with more caution.

Among property subtypes with at least 1,000 transactions, Duplex had the highest median close price at $910,000.

### Highest median price per square foot

| Rank | Property subtype | Median price/sq. ft. | Transactions |
|---:|---|---:|---:|
| 1 | Condominium | $564.17 | 73,531 |
| 2 | Townhouse | $560.90 | 26,228 |
| 3 | Duplex | $542.02 | 2,480 |

Although condominiums had a lower median close price than single-family residences, they recorded the highest median price per square foot among the major property subtype groups.

### Fastest property subtypes by average days on market

This comparison includes property subtypes with at least 100 transactions.

| Rank | Property subtype | Average DOM | Median DOM | Transactions |
|---:|---|---:|---:|---:|
| 1 | Townhouse | 32.27 | 17 | 26,228 |
| 2 | Single Family Residence | 36.10 | 17 | 335,138 |
| 3 | Stock Cooperative | 38.39 | 20 | 1,763 |

### Slowest property subtypes by average days on market

| Rank | Property subtype | Average DOM | Transactions |
|---:|---|---:|---:|
| 1 | Mixed Use | 85.73 | 222 |
| 2 | Cabin | 79.41 | 507 |
| 3 | Manufactured on Land | 59.06 | 5,783 |

#### Property subtype highlights

- Single-family residences were the clear market leader in both transaction count and total sales volume.
- Condominiums ranked second in transaction count but first in median price per square foot among the major subtypes.
- Townhouses had the shortest average days on market among the three largest property groups.
- Manufactured homes were substantially less expensive but took longer to sell.
- Mixed-use and cabin results were based on relatively small samples and should not be compared directly with the major residential segments without additional review.
- A total of 861 transactions, or approximately 0.19%, had a missing or unknown property subtype.

---

## 3. County Rankings

Source file: [week6_summary_by_county.csv](./week6_summary_by_county.csv)

The county summary contains 63 county groups and reconciles to 447,395 unique transactions.

To prevent very small counties from appearing as market leaders based on only a few transactions, price and days-on-market rankings below are limited to counties with at least 5,000 transactions. Eleven counties met this threshold.

### Top 3 counties by transaction count

| Rank | County | Transactions | Transaction share |
|---:|---|---:|---:|
| 1 | Los Angeles | 110,975 | 24.80% |
| 2 | Riverside | 62,008 | 13.86% |
| 3 | San Diego | 55,526 | 12.41% |

Los Angeles alone represented almost one quarter of all analyzed transactions.

The five largest counties by transaction count—Los Angeles, Riverside, San Diego, Orange, and San Bernardino—represented approximately 71.60% of all unique transactions.

### Top 3 counties by total sales volume

| Rank | County | Total sales volume | Transactions |
|---:|---|---:|---:|
| 1 | Los Angeles | $147.03B | 110,975 |
| 2 | San Diego | $81.89B | 55,526 |
| 3 | Orange | $77.67B | 50,344 |

Los Angeles was the largest county by both transaction count and total sales volume.

The five largest counties by sales volume represented approximately 72.94% of the total $533.39 billion sales volume.

### Highest median close prices

Among counties with at least 5,000 transactions:

| Rank | County | Median close price | Transactions |
|---:|---|---:|---:|
| 1 | San Mateo | $1,700,000 | 7,798 |
| 2 | Santa Clara | $1,600,000 | 19,650 |
| 3 | Orange | $1,180,000 | 50,344 |

San Mateo had the highest median close price among the major counties, followed by Santa Clara and Orange.

For comparison:

- Los Angeles median close price: $905,000
- San Diego median close price: $900,000
- Riverside median close price: $600,000
- San Bernardino median close price: $532,506

### Highest median price per square foot

Among counties with at least 5,000 transactions:

| Rank | County | Median price/sq. ft. | Transactions |
|---:|---|---:|---:|
| 1 | San Mateo | $1,052.63 | 7,798 |
| 2 | Santa Clara | $965.82 | 19,650 |
| 3 | Alameda | $700.86 | 21,197 |

San Mateo ranked first in both median close price and median price per square foot.

For comparison:

- Orange: $674.14 per square foot
- Los Angeles: $609.10 per square foot
- San Diego: $590.83 per square foot
- San Bernardino: $332.03 per square foot
- Riverside: $321.08 per square foot

### Fastest counties by average days on market

Among counties with at least 5,000 transactions:

| Rank | County | Average DOM | Median DOM | Transactions |
|---:|---|---:|---:|---:|
| 1 | Santa Clara | 21.95 | 10 | 19,650 |
| 2 | Alameda | 25.72 | 14 | 21,197 |
| 3 | San Mateo | 27.97 | 12 | 7,798 |

Santa Clara had the fastest market among the major counties, with an average DOM of 21.95 days and a median DOM of only 10 days.

### Slowest counties by average days on market

| Rank | County | Average DOM | Median DOM | Transactions |
|---:|---|---:|---:|---:|
| 1 | Riverside | 48.51 | 30 | 62,008 |
| 2 | San Bernardino | 46.14 | 24 | 41,496 |
| 3 | Ventura | 43.04 | 28 | 14,008 |

Riverside had the longest average and median days on market among the major counties.

### County leaders summary

| Market measure | Leading county | Result |
|---|---|---:|
| Most transactions | Los Angeles | 110,975 |
| Highest total sales volume | Los Angeles | $147.03B |
| Highest median close price | San Mateo | $1,700,000 |
| Highest median price/sq. ft. | San Mateo | $1,052.63 |
| Shortest average DOM | Santa Clara | 21.95 |
| Shortest median DOM | Santa Clara | 10 |
| Longest average DOM | Riverside | 48.51 |
| Longest median DOM | Riverside | 30 |

The price and DOM leader rankings in this table use the minimum 5,000-transaction threshold.

---

## 4. Listing Office Rankings

Complete file: [week6_summary_by_list_office.csv](./week6_summary_by_list_office.csv)

Top 100 file: [week6_top100_list_offices.csv](./week6_top100_list_offices.csv)

The complete listing-office summary contains 19,155 office groups.

### Top 3 listing offices by total sales volume

| Rank | Listing office | Transactions | Total sales volume | Volume share | Transaction share | Median close price | Median price/sq. ft. | Average DOM |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Compass | 31,705 | $58.73B | 11.01% | 7.09% | $1,350,000 | $757.28 | 30.66 |
| 2 | Coldwell Banker Realty | 20,191 | $33.55B | 6.29% | 4.51% | $1,200,000 | $694.14 | 34.53 |
| 3 | Keller Williams Realty | 8,754 | $9.05B | 1.70% | 1.96% | $875,000 | $540.39 | 31.51 |

The same three offices also ranked first, second, and third by transaction count.

### Listing-office leader summary

| Market measure | Leader | Result |
|---|---|---:|
| Highest total sales volume | Compass | $58.73B |
| Most transactions | Compass | 31,705 |
| Highest sales-volume share | Compass | 11.01% |
| Second-highest sales volume | Coldwell Banker Realty | $33.55B |
| Third-highest sales volume | Keller Williams Realty | $9.05B |

### Listing-office concentration

| Ranking group | Sales-volume share | Transaction share |
|---|---:|---:|
| Top 1 | 11.01% | 7.09% |
| Top 5 | 22.13% | 15.93% |
| Top 10 | 28.09% | 20.18% |
| Top 100 | 52.87% | 40.88% |

### Listing-office market structure

- Total listing-office groups: 19,155
- Offices with at least 500 transactions: 111
- Offices with at least 100 transactions: 610
- Office labels with only one transaction: 5,672
- Compass and Coldwell Banker Realty together represented approximately 17.30% of total listing-side sales volume.
- The Top 100 listing offices represented more than half of total sales volume but only 40.88% of transactions.
- This indicates that the largest listing offices were disproportionately involved in higher-value transactions.
- Office labels are based on the source MLS values and have not yet been fully consolidated for spelling, punctuation, or branding variations.

---

## 5. Buyer Office Rankings

Complete file: [week6_summary_by_buyer_office.csv](./week6_summary_by_buyer_office.csv)

Top 100 file: [week6_top100_buyer_offices.csv](./week6_top100_buyer_offices.csv)

The complete buyer-office summary contains 21,868 office groups.

### Top 3 valid buyer offices by total sales volume

The official Top 100 file excludes missing, placeholder, and `NONMEMBER` office labels.

| Rank | Buyer office | Transactions | Total sales volume | Volume share | Transaction share | Median close price | Median price/sq. ft. | Average DOM |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Compass | 29,594 | $53.96B | 10.12% | 6.61% | $1,337,750 | $752.31 | 32.00 |
| 2 | Coldwell Banker Realty | 16,222 | $27.79B | 5.21% | 3.63% | $1,199,000 | $688.70 | 34.71 |
| 3 | Keller Williams Realty | 6,899 | $8.62B | 1.62% | 1.54% | $840,000 | Not highlighted | 34.73 |

Compass, Coldwell Banker Realty, and Keller Williams Realty were also the three valid offices with the largest transaction counts.

### Buyer-office leader summary

| Market measure | Leader | Result |
|---|---|---:|
| Highest valid-office sales volume | Compass | $53.96B |
| Most valid-office transactions | Compass | 29,594 |
| Highest valid-office volume share | Compass | 10.12% |
| Second-highest valid-office volume | Coldwell Banker Realty | $27.79B |
| Third-highest valid-office volume | Keller Williams Realty | $8.62B |

### Buyer-office concentration

| Ranking group | Sales-volume share | Transaction share |
|---|---:|---:|
| Top 1 | 10.12% | 6.61% |
| Top 5 | 20.01% | 14.89% |
| Top 10 | 25.90% | 20.82% |
| Top 100 | 51.76% | 42.07% |

### Buyer-office market structure

- Total buyer-office groups: 21,868
- Offices with at least 500 transactions: 107
- Offices with at least 100 transactions: 585
- Office labels with only one transaction: 7,796
- Compass and Coldwell Banker Realty together represented approximately 15.33% of total buyer-side sales volume.
- The Top 100 buyer offices represented 51.76% of sales volume and 42.07% of transactions.
- Buyer-office records were more fragmented than listing-office records.

### Missing and nonmember buyer offices

The complete Buyer Office file includes unidentified and nonmember categories so that their data-quality impact remains visible.

| Category | Transactions | Transaction share | Total sales volume |
|---|---:|---:|---:|
| Missing/Unknown | 7,142 | 1.60% | $9.43B |
| All `NONMEMBER` labels | 11,046 | 2.47% | $7.54B |
| `NONMEMBER MRML` alone | 9,748 | 2.18% | $6.20B |

Important ranking detail:

- `Missing/Unknown` would rank third by total sales volume in the unfiltered Buyer Office summary.
- `NONMEMBER MRML` would rank third by transaction count in the unfiltered summary.
- Neither category represents a normal named brokerage.
- Both are therefore excluded from the official Buyer Office Top 100 ranking.
- After these exclusions, Keller Williams Realty is the valid third-ranked buyer office.

---

## 6. Overall Market Leaders

| Category | First place | Second place | Third place |
|---|---|---|---|
| Property subtype by transactions | Single Family Residence | Condominium | Townhouse |
| Property subtype by sales volume | Single Family Residence | Condominium | Townhouse |
| County by transactions | Los Angeles | Riverside | San Diego |
| County by sales volume | Los Angeles | San Diego | Orange |
| County by median price | San Mateo | Santa Clara | Orange |
| County by median price/sq. ft. | San Mateo | Santa Clara | Alameda |
| Fastest major county by average DOM | Santa Clara | Alameda | San Mateo |
| Slowest major county by average DOM | Riverside | San Bernardino | Ventura |
| Listing office by sales volume | Compass | Coldwell Banker Realty | Keller Williams Realty |
| Buyer office by sales volume | Compass | Coldwell Banker Realty | Keller Williams Realty |

County price and DOM rankings are limited to counties with at least 5,000 transactions.

---

## Interpretation Note

These results are suitable for sharing as preliminary Week 6 descriptive findings, with the following caveats:

- Week 7 outlier detection has not yet been applied.
- Total sales volume and average-based measures may still be influenced by extreme values.
- Average price ratios should not be treated as final market conclusions until unusually small price denominators are reviewed.
- Median price, median price per square foot, and transaction count are currently more reliable for high-level comparisons.
- Small segments can produce unstable medians, so subtype rankings use at least 100 transactions and major county rankings use at least 5,000 transactions.
- Office-name spelling and branding variations have not yet been consolidated.
- The results describe the available MLS transaction data and do not establish causal relationships.


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


