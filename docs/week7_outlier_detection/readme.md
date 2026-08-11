# Week 7 - Outlier Detection Before/After Comparison

## Executive summary

The Week 7 process evaluated 447,771 residential sold records and retained 376,529 records in the clean analysis dataset. A total of 71,242 rows (15.91%) were excluded from the separate clean dataset because at least one key numeric field was flagged or the row was a superseded duplicate snapshot. The complete flagged dataset still preserves every source record.

## Method

For ClosePrice, LivingArea, and DaysOnMarket, the script calculated Q1, Q3, IQR, and the standard 1.5 x IQR bounds. It also recorded extreme percentile flags below p0.1 or above p99.9 because strongly right-skewed housing measures can produce negative IQR lower bounds that fail to identify implausibly small positive values.

Business validity flags are separate and transparent: ClosePrice and LivingArea must be greater than zero, while DaysOnMarket must be zero or greater. Missing values are reported but are not treated as outliers in this Week 7 workflow.

The intended downstream grain is one row per ListingKey. Repeated ListingKey snapshots remain visible in the complete flagged file, while the clean file keeps the last (newest loaded) snapshot.

## Dataset size comparison

| Measure | Before | After | Change |
|---|---:|---:|---:|
| Rows | 447,771 | 376,529 | -71,242 (15.91%) |
| Numeric outlier rows | 70,921 | 0 | -70,921 |
| Superseded duplicate snapshots | 376 | 0 | -376 |

## Median comparison

| Field | Before median | After median | Change |
|---|---:|---:|---:|
| ClosePrice | $825,000.00 | $789,000.00 | -$36,000.00 (-4.36%) |
| LivingArea | 1,646.00 sq ft | 1,573.00 sq ft | -73.00 sq ft (-4.43%) |
| DaysOnMarket | 18.00 days | 16.00 days | -2.00 days (-11.11%) |

## Flag summary

| Field | IQR flags | Extreme-percentile flags | Business-rule invalid | Combined field flags |
|---|---:|---:|---:|---:|
| ClosePrice | 33,479 | 886 | 0 | 33,927 |
| LivingArea | 19,568 | 817 | 0 | 19,937 |
| DaysOnMarket | 34,146 | 445 | 0 | 34,146 |

Because one row can be flagged in more than one field, field counts do not add directly to the 70,921 unique numeric-outlier rows. 15,104 rows were flagged in multiple fields.

The dataset also contained 376 older duplicate snapshots; 55 of those were already numeric outliers. Exclusion totals therefore use the union of the two conditions rather than adding their counts.

## Interpretation and limitations

The clean dataset is appropriate for typical-market summaries and the next Tableau phase. The flagged dataset should remain the audit source for luxury, distressed-sale, and data-quality review because a statistical outlier is not automatically an incorrect transaction.

The thresholds are global across the full residential sold dataset. Property-subtype or geographic analyses may later use segment-specific thresholds if the business question requires them, but those alternate thresholds should not silently replace the Week 7 global method.
