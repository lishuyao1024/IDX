"""
Create accurate numeric-distribution statistics for the Week 1 combined
Residential Sold and Listing datasets.

The resulting JSON is an intermediate used to build a two-sheet Excel report.
Extreme outliers are flagged with the standard 1.5 * IQR rule; source rows are
not removed or modified.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


FIELDS = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "DaysOnMarket",
    "YearBuilt",
]

DATASETS = {
    "Sold": "CRMLSSold_Residential_202401_202605.csv",
    "Listing": "CRMLSListing_Residential_202401_202605.csv",
}

CHART_SIZE = (1400, 760)
NAVY = "#17365D"
BLUE = "#4472C4"
LIGHT_BLUE = "#D9EAF7"
ORANGE = "#ED7D31"
GRID = "#D9E2F3"
TEXT = "#222222"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a common Windows font, falling back to Pillow's bundled font."""
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _fmt(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if magnitude >= 1_000:
        return f"{value / 1_000:.1f}K"
    if magnitude >= 10:
        return f"{value:,.1f}"
    return f"{value:,.2f}"


def create_distribution_chart(
    values: pd.Series,
    dataset: str,
    field: str,
    output_path: Path,
) -> None:
    """Create a histogram and horizontal boxplot from all valid source values."""
    valid = values.dropna().to_numpy(dtype="float64")
    q01, q1, median, q3, q99 = np.quantile(valid, [0.01, 0.25, 0.50, 0.75, 0.99])
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    outliers = int(((valid < lower_fence) | (valid > upper_fence)).sum())

    # The central 98% keeps the histogram readable while the note preserves
    # transparency about values outside the displayed range.
    plot_low, plot_high = q01, q99
    if plot_low == plot_high:
        plot_low, plot_high = float(valid.min()), float(valid.max())
    if plot_low == plot_high:
        plot_low -= 0.5
        plot_high += 0.5
    central = valid[(valid >= plot_low) & (valid <= plot_high)]
    counts, edges = np.histogram(central, bins=30, range=(plot_low, plot_high))

    image = Image.new("RGB", CHART_SIZE, "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(30, bold=True)
    heading_font = _font(21, bold=True)
    body_font = _font(17)
    small_font = _font(14)

    draw.rectangle((0, 0, CHART_SIZE[0], 72), fill=NAVY)
    draw.text(
        (34, 19),
        f"{dataset} - {field} Distribution",
        fill="white",
        font=title_font,
    )

    # Histogram panel.
    left, top, right, bottom = 80, 140, 1320, 505
    draw.text((left, 96), "Histogram (P01-P99 display range)", fill=TEXT, font=heading_font)
    max_count = max(int(counts.max()), 1)
    for step in range(5):
        y = bottom - step * (bottom - top) / 4
        draw.line((left, y, right, y), fill=GRID, width=1)
        label = f"{int(max_count * step / 4):,}"
        draw.text((left - 12, y), label, fill=TEXT, font=small_font, anchor="rm")
    bar_width = (right - left) / len(counts)
    for index, count in enumerate(counts):
        x0 = left + index * bar_width + 1
        x1 = left + (index + 1) * bar_width - 1
        y0 = bottom - (count / max_count) * (bottom - top)
        draw.rectangle((x0, y0, x1, bottom), fill=BLUE)
    draw.line((left, bottom, right, bottom), fill=TEXT, width=2)
    for step in range(6):
        x = left + step * (right - left) / 5
        value = plot_low + step * (plot_high - plot_low) / 5
        draw.line((x, bottom, x, bottom + 7), fill=TEXT, width=1)
        draw.text((x, bottom + 12), _fmt(value), fill=TEXT, font=small_font, anchor="ma")

    # Boxplot panel. Whiskers use the IQR fences but are clipped to the actual
    # non-outlier data, matching standard boxplot behavior.
    draw.text((left, 555), "Boxplot (IQR method)", fill=TEXT, font=heading_font)
    axis_left, axis_right, axis_y = 150, 1250, 650
    non_outlier = valid[(valid >= lower_fence) & (valid <= upper_fence)]
    whisker_low = float(non_outlier.min()) if non_outlier.size else float(valid.min())
    whisker_high = float(non_outlier.max()) if non_outlier.size else float(valid.max())
    scale_low = min(whisker_low, q1)
    scale_high = max(whisker_high, q3)
    if scale_low == scale_high:
        scale_high = scale_low + 1

    def xpos(value: float) -> float:
        return axis_left + (value - scale_low) / (scale_high - scale_low) * (
            axis_right - axis_left
        )

    draw.line((axis_left, axis_y, axis_right, axis_y), fill=GRID, width=2)
    draw.line((xpos(whisker_low), axis_y, xpos(q1), axis_y), fill=TEXT, width=3)
    draw.line((xpos(q3), axis_y, xpos(whisker_high), axis_y), fill=TEXT, width=3)
    for value in (whisker_low, whisker_high):
        x = xpos(value)
        draw.line((x, axis_y - 25, x, axis_y + 25), fill=TEXT, width=3)
    draw.rectangle((xpos(q1), axis_y - 38, xpos(q3), axis_y + 38), fill=LIGHT_BLUE, outline=BLUE, width=3)
    draw.line((xpos(median), axis_y - 38, xpos(median), axis_y + 38), fill=ORANGE, width=4)
    for value, label in [
        (whisker_low, f"Whisker {_fmt(whisker_low)}"),
        (q1, f"Q1 {_fmt(q1)}"),
        (median, f"Median {_fmt(median)}"),
        (q3, f"Q3 {_fmt(q3)}"),
        (whisker_high, f"Whisker {_fmt(whisker_high)}"),
    ]:
        draw.text((xpos(value), axis_y + 49), label, fill=TEXT, font=small_font, anchor="ma")

    excluded = int(valid.size - central.size)
    note = (
        f"Valid values: {valid.size:,} | Histogram values outside P01-P99: "
        f"{excluded:,} | IQR outliers: {outliers:,} ({outliers / valid.size:.2%})"
    )
    draw.text((left, 722), note, fill=TEXT, font=body_font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def analyze_file(path: Path, dataset: str, charts_dir: Path | None = None) -> dict:
    """Read selected fields and return distribution and IQR-outlier statistics."""
    if not path.exists():
        raise FileNotFoundError(path)

    header = pd.read_csv(path, nrows=0).columns.tolist()
    available_fields = [field for field in FIELDS if field in header]
    frame = pd.read_csv(path, usecols=available_fields, low_memory=False)
    row_count = len(frame)
    results = []

    for field in FIELDS:
        if field not in frame.columns:
            results.append(
                {
                    "field": field,
                    "status": "Column not present",
                    "source_rows": row_count,
                    "valid_count": 0,
                    "missing_or_non_numeric_count": row_count,
                }
            )
            continue

        values = pd.to_numeric(frame[field], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
        valid = values.dropna()
        valid_count = int(valid.size)
        missing_count = int(row_count - valid_count)

        if valid_count == 0:
            results.append(
                {
                    "field": field,
                    "status": "No valid numeric values",
                    "source_rows": row_count,
                    "valid_count": 0,
                    "missing_or_non_numeric_count": missing_count,
                }
            )
            continue

        if charts_dir is not None:
            create_distribution_chart(
                values=valid,
                dataset=dataset,
                field=field,
                output_path=charts_dir / dataset.lower() / f"{field}.png",
            )

        quantiles = valid.quantile(
            [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]
        )
        q1 = float(quantiles.loc[0.25])
        q3 = float(quantiles.loc[0.75])
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        low_outliers = int((valid < lower_fence).sum())
        high_outliers = int((valid > upper_fence).sum())
        total_outliers = low_outliers + high_outliers

        results.append(
            {
                "field": field,
                "status": "Analyzed",
                "source_rows": row_count,
                "valid_count": valid_count,
                "missing_or_non_numeric_count": missing_count,
                "missing_percentage": missing_count / row_count,
                "min": float(valid.min()),
                "p01": float(quantiles.loc[0.01]),
                "p05": float(quantiles.loc[0.05]),
                "p25": q1,
                "mean": float(valid.mean()),
                "median_p50": float(quantiles.loc[0.50]),
                "p75": q3,
                "p95": float(quantiles.loc[0.95]),
                "p99": float(quantiles.loc[0.99]),
                "max": float(valid.max()),
                "iqr": float(iqr),
                "lower_fence": float(lower_fence),
                "upper_fence": float(upper_fence),
                "low_outlier_count": low_outliers,
                "high_outlier_count": high_outliers,
                "total_outlier_count": total_outliers,
                "outlier_percentage_of_valid": total_outliers / valid_count,
            }
        )

    return {
        "source_file": path.name,
        "row_count": row_count,
        "fields": results,
    }


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=script_dir / "outputs" / "week1",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=script_dir / "numeric_distribution_results.json",
    )
    parser.add_argument(
        "--charts-dir",
        type=Path,
        default=script_dir / "charts",
        help="Folder for histogram and boxplot PNG files.",
    )
    args = parser.parse_args()

    report = {
        dataset: analyze_file(
            args.input_dir / filename,
            dataset=dataset,
            charts_dir=args.charts_dir,
        )
        for dataset, filename in DATASETS.items()
    }
    args.output_json.write_text(
        json.dumps(report, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    for dataset, result in report.items():
        analyzed = sum(field["status"] == "Analyzed" for field in result["fields"])
        print(
            f"{dataset}: {result['row_count']:,} rows; "
            f"{analyzed}/{len(FIELDS)} requested fields analyzed."
        )
    print(f"Intermediate results: {args.output_json}")


if __name__ == "__main__":
    main()
