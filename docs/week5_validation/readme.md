# Week 5 - Data Cleaning Validation Results

This folder contains the Week 5 validation results for the CRMLS Residential Sold and Listing datasets.

Week 5 focused on removing clearly invalid records and non-useful columns while retaining date and geographic issues as quality flags for further review.

## Cleaning Logic

### 1. Invalid Records Removed

Records were removed only when they violated a clear numeric rule or were missing a required field.

Numeric removal rules:

- `ClosePrice <= 0`
- `LivingArea <= 0`
- `DaysOnMarket < 0`
- `BedroomsTotal < 0`
- `BathroomsTotalInteger < 0`

Required Sold fields:

- `ListingKey`
- `CloseDate`
- `ClosePrice`

Required Listing fields:

- `ListingKey`
- `ListingContractDate`
- `ListPrice`

### Removed Sold Records

| Removal reason | Records removed |
|---|---:|
| `ClosePrice <= 0` | 1 |
| `LivingArea <= 0` | 165 |
| `DaysOnMarket < 0` | 51 |
| Missing required field | 2 |
| **Total** | **219** |

### Removed Listing Records

| Removal reason | Records removed |
|---|---:|
| `LivingArea <= 0` | 394 |
| `DaysOnMarket < 0` | 28 |
| **Total** | **422** |

A total of **641 records** were removed.

## 2. Columns Removed

Columns were removed when:

- Their missing-value rate was greater than 90%
- They were not required for core market analysis

The redundant `ListingKeyNumeric` field was also removed because it contained the same values as `ListingKey`.

### Sold Columns Removed

- `WaterfrontYN`
- `BasementYN`
- `FireplacesTotal`
- `AboveGradeFinishedArea`
- `ListingKeyNumeric`
- `TaxAnnualAmount`
- `BuilderName`
- `TaxYear`
- `BuildingAreaTotal`
- `ElementarySchoolDistrict`
- `CoBuyerAgentFirstName`
- `BelowGradeFinishedArea`
- `BusinessType`
- `CoveredSpaces`
- `LotSizeDimensions`
- `MiddleOrJuniorSchoolDistrict`

A total of **16 Sold columns** were removed.

### Listing Columns Removed

- `FireplacesTotal`
- `AboveGradeFinishedArea`
- `ListingKeyNumeric`
- `TaxAnnualAmount`
- `BuilderName`
- `TaxYear`
- `BuildingAreaTotal`
- `ElementarySchoolDistrict`
- `CoBuyerAgentFirstName`
- `BelowGradeFinishedArea`
- `BusinessType`
- `CoveredSpaces`
- `LotSizeDimensions`
- `MiddleOrJuniorSchoolDistrict`

A total of **14 Listing columns** were removed.

## 3. Records Retained with Quality Flags

Date and geographic issues were not automatically deleted.

These records may still be useful for price, property, or market-volume analysis.

### Date Quality Flags

- `listing_after_close_flag`
- `purchase_after_close_flag`
- `negative_timeline_flag`

### Geographic Quality Flags

- `missing_coordinates_flag`
- `zero_coordinates_flag`
- `positive_longitude_flag`
- `out_of_state_flag`
- `implausible_coordinates_flag`
- `outside_california_bounds_flag`
- `geographic_review_flag`

Flagged geographic records should be reviewed or excluded before map-based analysis.

## Final Results

| Dataset | Input rows | Removed rows | Final rows | Columns removed | Final columns |
|---|---:|---:|---:|---:|---:|
| Sold | 447,990 | 219 | 447,771 | 16 | 88 |
| Listing | 616,099 | 422 | 615,677 | 14 | 79 |

The final column counts include the newly created data-quality flag columns.

## Validation Results

Independent validation confirmed:

- Correct final row counts
- Correct final column counts
- Zero quality-flag mismatches
- Zero invalid records remaining
- Zero missing-value summary mismatches
- All removed records had documented reasons

## Files in This Folder

### `week5_cleaning_validation_summary.csv`

Provides the overall before-and-after cleaning results, including:

- Input rows
- Removed rows
- Final rows
- Input and final column counts
- Duplicate `ListingKey` observations retained for review

### `week5_quality_flag_summary.csv`

Provides the count and percentage for every numeric, date, completeness, and geographic quality flag.

It also shows whether each issue was:

- Removed
- Retained and flagged for review

### `week5_cleaned_missing_value_summary.csv`

Provides the final missing-value count and percentage for every column in both cleaned datasets.

## Data Availability

The full cleaned Sold and Listing CSV files are not included in this repository because they are large and contain confidential MLS data.

Only aggregated validation summaries are stored in GitHub.

## Next Step

The validated datasets will be used for:

- Week 6 feature engineering
- Week 7 outlier detection
- Market analysis
- Tableau dashboard development
