# AURELIA - Week 2, Step 4: DatasetProfiler
# Save as: D:\AURELIA\ingestion\profiler.py
#
# This actually INSPECTS the real data - nothing here is assumed or
# hardcoded like our row_count=284807 guess was. Every number below is
# computed directly from the file.

from __future__ import annotations
import pandas as pd
from pydantic import BaseModel


class DataProfile(BaseModel):
    """
    The structured result of profiling a dataset. This becomes part of
    the permanent record - later, this is what gets attached to a
    Dataset once profiling completes (Dataset.status -> PROFILED).
    """
    row_count: int
    column_count: int
    column_names: list[str]
    dtypes: dict[str, str]

    missing_value_counts: dict[str, int]
    missing_value_percentages: dict[str, float]

    # Class balance - specific to classification datasets with a target column
    target_column: str
    class_counts: dict[str, int]
    class_balance_ratio: float  # minority class % of total


class DatasetProfiler:
    """
    Computes real statistics from a real file. For now this operates on
    a local file path - later this will run as a Modal Function against
    the file inside the Volume, since profiling a huge dataset shouldn't
    happen on your laptop either.
    """

    def profile(self, file_path: str, target_column: str) -> DataProfile:
        df = pd.read_csv(file_path)

        row_count = len(df)
        column_count = len(df.columns)
        column_names = list(df.columns)
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

        missing_counts = df.isnull().sum().to_dict()
        missing_counts = {k: int(v) for k, v in missing_counts.items()}
        missing_percentages = {
            k: round((v / row_count) * 100, 4) for k, v in missing_counts.items()
        }

        class_counts_raw = df[target_column].value_counts().to_dict()
        class_counts = {str(k): int(v) for k, v in class_counts_raw.items()}
        minority_count = min(class_counts.values())
        class_balance_ratio = round((minority_count / row_count) * 100, 4)

        return DataProfile(
            row_count=row_count,
            column_count=column_count,
            column_names=column_names,
            dtypes=dtypes,
            missing_value_counts=missing_counts,
            missing_value_percentages=missing_percentages,
            target_column=target_column,
            class_counts=class_counts,
            class_balance_ratio=class_balance_ratio,
        )


if __name__ == "__main__":
    # Quick manual check - run with: python -m ingestion.profiler
    profiler = DatasetProfiler()
    profile = profiler.profile("data_raw/creditcard.csv", target_column="Class")

    print(f"Row count (verified, not assumed): {profile.row_count}")
    print(f"Column count (verified, not assumed): {profile.column_count}")
    print(f"Class balance - minority class is {profile.class_balance_ratio}% of total data")
    print(f"Class counts: {profile.class_counts}")
    print(f"Columns with any missing values: "
          f"{[k for k, v in profile.missing_value_counts.items() if v > 0] or 'None'}")