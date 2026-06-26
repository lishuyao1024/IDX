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
