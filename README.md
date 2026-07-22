# IDX Exchange MLS Analytics Project

## Project Overview
This repository contains my project work for the IDX Exchange Data Analyst Internship. The project focuses on analyzing MLS residential listing and sold transaction data, building housing market metrics, and developing Tableau dashboards for market and competitive intelligence.

## Data Source
The MLS data is provided through IDX Exchange's internal FTP pipeline. The original data is generated from the CoreLogic Trestle API and stored as monthly CSV files for listings and sold transactions.

Note: Raw CSV files and source data are confidential and are not uploaded to this repository.

## Project Workflow
1. Download monthly MLS listing and sold files from the company FTP server.
2. Use Python and Pandas to combine monthly files into two datasets: listings and sold.
3. Clean and validate the datasets.
4. Engineer housing market metrics.
5. Detect and flag outliers.
6. Build Tableau dashboards.
7. Prepare a final market intelligence report and presentation.

## Repository Structure
- `scripts/`: Python scripts for data aggregation, cleaning, feature engineering, and outlier detection.
- `docs/`: Weekly notes and project documentation.
- `tableau/`: Tableau workbook files.
- `reports/`: Final market intelligence report.
- `requirements.txt`: Python package dependencies.

## Tools Used
- Python
- Pandas
- Tableau Public
- FileZilla
- GitHub

## Internship Deliverables
- Cleaned and analysis-ready datasets
- Market analysis Tableau dashboard
- Competitive analysis Tableau dashboard
- 1-page market intelligence report
- 5-minute final presentation

## Weekly Progress

### Week 1 - Monthly Dataset Aggregation
- Downloaded monthly MLS Listing and Sold CSV files from the IDX Exchange FTP server.
- Aggregated 29 months of data from January 2024 through May 2026.
- Combined monthly files into two Residential-only master datasets: Listings and Sold.
- Generated a row count validation summary to confirm records before and after the Residential filter.
- Raw and processed CSV files are not uploaded because the MLS data is confidential.
  
### Weeks 2 - Dataset Structuring and Validation
- Reviewed the structure of the Residential Sold and Listing datasets.
- Confirmed 430,427 Sold records and 591,977 Listing records.
- Generated column data-type and missing-value summaries.
- Flagged 15 Sold columns and 13 Listing columns with more than 90% missing values.
- Analyzed numeric distributions for price, living area, lot size, bedrooms,
  bathrooms, days on market, and year built.
- Generated histograms and boxplots using percentile and IQR methods.
- Completed foundational EDA covering residential share, median and average
  prices, days on market, sold-to-list comparison, date consistency, and
  county median prices.
- Mortgage-rate enrichment was intentionally excluded.

### Week 3 - Mortgage Rate Enrichment
- Retrieved the FRED MORTGAGE30US weekly 30-year fixed mortgage rate series.
- Aggregated weekly mortgage rates into calendar-month averages.
- Created a `year_month` key using `CloseDate` for Sold records and `ListingContractDate` for Listing records.
- Left-merged monthly mortgage rates onto both Residential datasets.
- Validated that row counts remained unchanged and that no mortgage-rate values were missing after the merge.

### Week 4 Data Validation & Quality Assessment

Completed comprehensive validation on both the Listings and Sold datasets after mortgage rate enrichment.

Validation tasks included:

- Verified dataset structure (rows, columns, file size, and schema consistency)
- Checked numeric field conversions and identified invalid values
- Evaluated missing values across important variables
- Performed date consistency validation, including:
  - Listing Date vs. Close Date
  - Purchase Contract Date vs. Close Date
  - Listing Date vs. Purchase Contract Date
- Generated validation summary reports for both datasets

Validation reports are stored in:

```
docs/validation/week4_5/
```

The validated datasets will serve as the foundation for subsequent feature engineering, market analysis, and Tableau dashboard development.
