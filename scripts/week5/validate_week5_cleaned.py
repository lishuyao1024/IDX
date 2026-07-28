"""This script independently validates the Week 5 cleaned outputs and confirms that the cleaning rules were applied correctly."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
PIPELINE_PATH = BASE_DIR / "week5_quality_flags_and_cleaning.py"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("week5_pipeline", PIPELINE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import Week 5 pipeline: {PIPELINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    pipeline = load_pipeline_module()
    validation = pd.read_csv(
        BASE_DIR / "week5_cleaning_validation_summary.csv"
    ).set_index("dataset")
    column_review = pd.read_csv(BASE_DIR / "week5_column_review_summary.csv")
    expected_missing = pd.read_csv(
        BASE_DIR / "week5_cleaned_missing_value_summary.csv"
    )

    for dataset, output_path in pipeline.CLEANED_FILES.items():
        expected_rows = int(validation.loc[dataset, "cleaned_rows"])
        expected_columns = int(validation.loc[dataset, "cleaned_columns"])
        expected_dataset_missing = (
            expected_missing.loc[expected_missing["dataset"].eq(dataset)]
            .set_index("column")["missing_count"]
            .astype(int)
            .sort_index()
        )
        dropped_columns = set(
            column_review.loc[
                column_review["dataset"].eq(dataset)
                & column_review["review_action"].str.startswith("drop"),
                "column",
            ]
        )

        actual_rows = 0
        actual_nulls = None
        flag_mismatches = 0
        forbidden_rows = 0

        for chunk in pd.read_csv(
            output_path,
            chunksize=pipeline.CHUNK_SIZE,
            low_memory=False,
        ):
            actual_rows += len(chunk)
            original_flags = chunk[pipeline.FLAG_COLUMNS].astype(bool).copy()

            recomputed = pipeline.ensure_types(chunk.copy())
            recomputed = pipeline.add_numeric_flags(recomputed, dataset)
            recomputed = pipeline.add_date_flags(recomputed)
            recomputed = pipeline.add_geographic_flags(recomputed)

            for flag in pipeline.FLAG_COLUMNS:
                flag_mismatches += int(
                    (
                        original_flags[flag]
                        != recomputed[flag].astype(bool)
                    ).sum()
                )

            forbidden_rows += int(recomputed["remove_from_cleaned_flag"].sum())
            chunk_nulls = chunk.isna().sum()
            actual_nulls = (
                chunk_nulls
                if actual_nulls is None
                else actual_nulls.add(chunk_nulls, fill_value=0)
            )

        output_columns = pd.read_csv(output_path, nrows=0).columns.tolist()
        actual_columns = len(output_columns)
        present_dropped_columns = dropped_columns.intersection(output_columns)
        missing_flag_columns = set(pipeline.FLAG_COLUMNS).difference(output_columns)
        actual_nulls = actual_nulls.astype(int).sort_index()
        missing_mismatches = int(
            (actual_nulls != expected_dataset_missing).sum()
        )

        print(
            f"{dataset}: rows={actual_rows}/{expected_rows}, "
            f"columns={actual_columns}/{expected_columns}, "
            f"flag_mismatches={flag_mismatches}, "
            f"forbidden_rows={forbidden_rows}, "
            f"missing_mismatches={missing_mismatches}"
        )

        assert actual_rows == expected_rows
        assert actual_columns == expected_columns
        assert not present_dropped_columns
        assert not missing_flag_columns
        assert flag_mismatches == 0
        assert forbidden_rows == 0
        assert missing_mismatches == 0

    removed_audit = pd.read_csv(BASE_DIR / "week5_removed_records_audit.csv")
    expected_removed = int(validation["removed_rows"].sum())
    assert len(removed_audit) == expected_removed
    assert removed_audit["removal_reason"].notna().all()
    assert removed_audit["removal_reason"].str.strip().ne("").all()

    print(
        f"removed-record audit: rows={len(removed_audit)}/{expected_removed}"
    )
    print("Independent Week 5 validation passed.")


if __name__ == "__main__":
    main()
