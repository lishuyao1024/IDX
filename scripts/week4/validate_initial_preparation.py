"""Independent structural validation for the initial Weeks 4-5 outputs."""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
FILES = {
    "sold": BASE_DIR
    / "CRMLSSold_Residential_202401_202606_Initially_Prepared.csv",
    "listing": BASE_DIR
    / "CRMLSListing_Residential_202401_202606_Initially_Prepared.csv",
}


def main() -> None:
    structure = pd.read_csv(BASE_DIR / "dataset_structure_summary.csv").set_index(
        "dataset"
    )
    missing = pd.read_csv(BASE_DIR / "missing_value_summary.csv")

    for dataset, path in FILES.items():
        expected_rows = int(structure.loc[dataset, "prepared_row_count"])
        expected_columns = int(structure.loc[dataset, "prepared_column_count"])
        expected_missing = (
            missing.loc[missing["dataset"].eq(dataset)]
            .set_index("column")["missing_count"]
            .astype(int)
            .sort_index()
        )

        actual_rows = 0
        actual_nulls = None
        for chunk in pd.read_csv(path, chunksize=50_000, low_memory=False):
            actual_rows += len(chunk)
            chunk_nulls = chunk.isna().sum()
            actual_nulls = (
                chunk_nulls
                if actual_nulls is None
                else actual_nulls.add(chunk_nulls, fill_value=0)
            )

        actual_columns = len(pd.read_csv(path, nrows=0).columns)
        actual_nulls = actual_nulls.astype(int).sort_index()
        missing_mismatches = int((actual_nulls != expected_missing).sum())

        print(
            f"{dataset}: rows={actual_rows}/{expected_rows}, "
            f"columns={actual_columns}/{expected_columns}, "
            f"missing_mismatches={missing_mismatches}"
        )
        assert actual_rows == expected_rows
        assert actual_columns == expected_columns
        assert missing_mismatches == 0

    print("Independent validation passed.")


if __name__ == "__main__":
    main()
