# AURELIA - Week 2, Step 1: DatasetLoader decision logic
# Save as: D:\AURELIA\ingestion\loader.py
#
# New folder needed: D:\AURELIA\ingestion\
# Also add an empty __init__.py inside ingestion\ (same reason as domain\)

from __future__ import annotations
import os
from enum import Enum
from pathlib import Path


class LoadStrategy(str, Enum):
    """
    The possible ways we might load a dataset, depending on its size.
    We are only IMPLEMENTING the first two today. PYSPARK is defined now
    so the decision logic is complete, even though we don't build the
    actual distributed loading path yet - that's intentionally deferred.
    """
    PANDAS = "PANDAS"              # small enough to load fully into RAM
    POLARS_LAZY = "POLARS_LAZY"    # too big for pandas comfort, but still single-machine
    PYSPARK = "PYSPARK"            # too big for a single machine at all (not implemented yet)


# Thresholds are intentionally simple and explicit right now - real numbers,
# not guesses buried in code. These can be tuned later based on actual
# available RAM (which is itself something we could query from Modal).
SMALL_FILE_THRESHOLD_MB = 200      # below this -> pandas is fine
LARGE_FILE_THRESHOLD_MB = 20_000   # above this -> would need PySpark (20 GB)


def decide_load_strategy(file_path: str) -> LoadStrategy:
    """
    THE decision function. Given only a file path, look at its size on disk
    and decide which loading strategy is appropriate. This is deliberately
    a pure, deterministic function - no LLM, no guessing - exactly matching
    the master plan's point that dataset size -> execution engine is a
    SYSTEMS decision, not something we ask a language model about.
    """
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)

    if size_mb < SMALL_FILE_THRESHOLD_MB:
        return LoadStrategy.PANDAS
    elif size_mb < LARGE_FILE_THRESHOLD_MB:
        return LoadStrategy.POLARS_LAZY
    else:
        return LoadStrategy.PYSPARK


class UnsupportedStrategyError(Exception):
    """Raised when the decided strategy isn't implemented yet (e.g. PYSPARK)."""
    pass


class DatasetLoader:
    """
    Wraps the decision logic with actual loading. Right now it can execute
    PANDAS and POLARS_LAZY strategies. PYSPARK raises a clear error instead
    of silently doing the wrong thing - we NEVER want a large dataset to
    accidentally get loaded the naive way.
    """

    def load_preview(self, file_path: str, n_rows: int = 5):
        """
        Loads just a small preview + reports which strategy WOULD be used
        for the full load. This lets us test the decision logic without
        needing an actual huge file on disk right now.
        """
        strategy = decide_load_strategy(file_path)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

        if strategy == LoadStrategy.PANDAS:
            import pandas as pd
            df = pd.read_csv(file_path, nrows=n_rows)
            row_preview = df.to_dict(orient="records")

        elif strategy == LoadStrategy.POLARS_LAZY:
            import polars as pl
            # Lazy scan does NOT load the file into memory - it builds a
            # query plan. .head().collect() only materializes a few rows.
            lazy_df = pl.scan_csv(file_path)
            row_preview = lazy_df.head(n_rows).collect().to_dicts()

        else:
            raise UnsupportedStrategyError(
                f"Strategy {strategy} is not implemented yet. "
                f"File is {file_size_mb:.1f} MB - this needs a distributed "
                f"loading path (PySpark) that we haven't built."
            )

        return {
            "file_path": file_path,
            "file_size_mb": round(file_size_mb, 3),
            "strategy_used": strategy,
            "preview_rows": row_preview,
        }


if __name__ == "__main__":
    # Quick manual check - run with: python -m ingestion.loader
    # First, create a small dummy CSV file to test against.
    import csv

    test_path = "test_small.csv"
    with open(test_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "feature_1", "label"])
        for i in range(20):
            writer.writerow([i, i * 1.5, i % 2])

    loader = DatasetLoader()
    result = loader.load_preview(test_path, n_rows=3)

    print(f"File size: {result['file_size_mb']} MB")
    print(f"Strategy chosen: {result['strategy_used']}")
    print("Preview rows:")
    for row in result["preview_rows"]:
        print(f"  {row}")

    os.remove(test_path)