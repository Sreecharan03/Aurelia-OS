# AURELIA - Week 2, Step 1b: Proving the POLARS_LAZY branch works
# Save as: D:\AURELIA\ingestion\test_loader_branches.py
#
# This is a throwaway verification script, not part of the permanent system -
# its only job is to prove BOTH branches of decide_load_strategy actually work,
# not just the one that happened to trigger on our tiny test file.

from ingestion import loader
import csv
import os


def make_test_csv(path: str, n_rows: int = 20):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "feature_1", "label"])
        for i in range(n_rows):
            writer.writerow([i, i * 1.5, i % 2])


if __name__ == "__main__":
    test_path = "test_branch.csv"
    make_test_csv(test_path)

    # Temporarily force a tiny threshold so our small file gets classified
    # as needing POLARS_LAZY, proving that branch actually executes correctly.
    original_threshold = loader.SMALL_FILE_THRESHOLD_MB
    loader.SMALL_FILE_THRESHOLD_MB = 0  # force everything above 0 MB to skip pandas

    dl = loader.DatasetLoader()
    result = dl.load_preview(test_path, n_rows=3)

    print(f"Strategy chosen: {result['strategy_used']}")
    print("Preview rows (loaded via Polars lazy scan):")
    for row in result["preview_rows"]:
        print(f"  {row}")

    # Restore the real threshold so nothing else is affected
    loader.SMALL_FILE_THRESHOLD_MB = original_threshold

    os.remove(test_path)