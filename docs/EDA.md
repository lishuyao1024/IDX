# Week 2–3 Exploratory Data Analysis

This document summarizes the Week 2–3 exploratory data analysis for the IDX MLS analytics project.  
The analysis focuses on Residential MLS records and highlights dataset coverage, price behavior, market speed, sale-to-list price patterns, and basic data quality checks.

---

## 1. Residential Data Scope

The original MLS datasets were filtered to focus on `Residential` properties for both Listing and Sold records.

- Listing data:
  - Residential records account for approximately **63.6%** of all listing records.
  - Final Residential Listing dataset size: **591,977 records**.

- Sold data:
  - Residential records account for approximately **67.3%** of all sold records.
  - Final Residential Sold dataset size: **430,427 records**.

This confirms that Residential properties represent the majority of the available MLS records and provide a strong base for further housing market analysis.

---

## 2. Price Distribution

Sold home prices show a clear right-skewed distribution.

- Median `ClosePrice`: **$825,000**
- Mean `ClosePrice`: **about $1.19M**

The mean is noticeably higher than the median, which suggests that a smaller number of high-priced homes pull the average upward. For this reason, the median is often a more stable measure of the typical sold home price.

---

## 3. Days on Market

`DaysOnMarket` also shows a skewed pattern, with most homes moving relatively quickly while a smaller number remain on the market much longer.

- Sold data:
  - Median `DaysOnMarket`: **18 days**
  - Mean `DaysOnMarket`: **37.3 days**

- Listing data:
  - Median `DaysOnMarket`: **11 days**
  - Mean `DaysOnMarket`: **18.5 days**

The gap between the mean and median indicates that long-market listings increase the average.

---

## 4. Sale Price vs. List Price

The Sold dataset was also used to compare final sale price against list price.

- **40.1%** of sold homes closed above list price.
- **17.4%** closed at list price.
- **42.5%** closed below list price.

Overall, the market appears relatively balanced, with slightly more homes closing below list price than above list price.

---

## 5. Basic Data Quality Checks

A small number of date inconsistencies were identified during EDA.

- Listing date after close date: **64 records**
- Purchase date after close date: **239 records**
- Listing date after purchase date: **280 records**

These records represent a very small portion of the dataset. They should be flagged for review rather than removed automatically.

---

## 6. County-Level Price Differences

Median sold prices vary significantly by county. Among counties with at least 100 valid sold records, some of the highest median close prices include:

- San Mateo: **$1.7M**
- Santa Clara: **$1.6M**
- San Francisco: **about $1.2M**

This suggests strong regional variation in housing prices across the MLS market area.

---

## Summary

The Week 2–3 EDA confirms that the Residential subset is large enough and meaningful for continued analysis.  
Key patterns include right-skewed price distributions, skewed days-on-market behavior, meaningful sale-to-list price variation, and strong county-level price differences.

No raw MLS data, property-level records, addresses, or confidential identifiers are included in this summary.
