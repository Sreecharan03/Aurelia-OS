# AURELIA - Week 2, Step 5a: Synthetic dataset with DELIBERATE leakage
# Save as: D:\AURELIA\ingestion\synthetic_leaky_data.py
#
# This is a small, deliberately adversarial dataset - a first step toward
# the "Synthetic Data Lab" from the master plan. Its only purpose is to
# give our leakage detector a KNOWN-BAD case to catch, so passing the
# real clean dataset actually means something.

import csv
import random


def generate_leaky_dataset(path: str, n_rows: int = 500):
    random.seed(42)

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["feature_clean_1", "feature_clean_2", "feature_LEAKY", "target"])

        for _ in range(n_rows):
            target = random.randint(0, 1)

            feature_clean_1 = random.uniform(0, 100)
            feature_clean_2 = random.uniform(-50, 50)

            # THE DELIBERATE LEAK: this column is directly derived from
            # the target, with only tiny noise added. A real leakage
            # detector MUST catch this - it's the most obvious possible case.
            feature_leaky = target * 1000 + random.uniform(-0.5, 0.5)

            writer.writerow([feature_clean_1, feature_clean_2, feature_leaky, target])

    print(f"Generated leaky synthetic dataset at: {path}")


if __name__ == "__main__":
    generate_leaky_dataset("data_raw/synthetic_leaky.csv")