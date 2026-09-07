# AURELIA - Week 2, Step 9: The Synthetic Data Lab
# Save as: D:\AURELIA\ingestion\synthetic_data_lab.py
#
# 10 deliberately adversarial datasets, per the master plan. Each one
# exists to test a SPECIFIC failure mode our system must eventually
# handle. Building these BEFORE more detectors exist is intentional:
# they double as a concrete to-do list. Where we don't yet have a
# detector for what a dataset tests, that's stated explicitly below -
# not silently glossed over.
#
# Every generator is deterministic (fixed seed) so results are
# reproducible across runs - the same principle as everywhere else
# in this project.

from __future__ import annotations
import csv
import random
import string


SEED = 2026


def _rng() -> random.Random:
    # A FRESH Random instance per generator call, not the global random
    # module - this means generating dataset 5 never affects the
    # randomness of dataset 6, even if called in a different order.
    return random.Random(SEED)


# ---------------------------------------------------------------------
# 1. NORMAL - a clean baseline with no deliberate problems.
# Purpose: every detector should stay SILENT on this one. If any
# detector flags something here, that's a false positive bug.
# ---------------------------------------------------------------------
def generate_normal(path: str, n_rows: int = 5000):
    rng = _rng()
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["feature_1", "feature_2", "feature_3", "target"])
        for _ in range(n_rows):
            target = rng.randint(0, 1)
            writer.writerow([
                round(rng.uniform(0, 100), 3),
                round(rng.uniform(-50, 50), 3),
                round(rng.gauss(0, 1), 3),
                target,
            ])


# ---------------------------------------------------------------------
# 2. SEVERE IMBALANCE (99:1) - tests whether the system correctly
# reports class balance rather than assuming ~50/50, and whether
# downstream experiment logic (not yet built) will need stratified
# splitting. Purpose: DatasetProfiler's class_balance_ratio should
# report ~1%, not silently misrepresent it.
# ---------------------------------------------------------------------
def generate_severe_imbalance(path: str, n_rows: int = 5000):
    rng = _rng()
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["feature_1", "feature_2", "target"])
        for _ in range(n_rows):
            target = 1 if rng.random() < 0.01 else 0  # ~1% positive class
            writer.writerow([round(rng.uniform(0, 10), 3), round(rng.uniform(0, 10), 3), target])


# ---------------------------------------------------------------------
# 3. MASSIVE MISSING VALUES - several columns with 40-90% missing data.
# Purpose: DatasetProfiler's missing_value_percentages must report
# these accurately. Also a stress test for SchemaDetector - a column
# that's MOSTLY missing shouldn't crash null_ratio calculations.
# ---------------------------------------------------------------------
def generate_missing_heavy(path: str, n_rows: int = 5000):
    rng = _rng()
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["mostly_missing", "half_missing", "complete", "target"])
        for _ in range(n_rows):
            mostly_missing = "" if rng.random() < 0.85 else round(rng.uniform(0, 1), 3)
            half_missing = "" if rng.random() < 0.5 else round(rng.uniform(0, 1), 3)
            complete = round(rng.uniform(0, 1), 3)
            target = rng.randint(0, 1)
            writer.writerow([mostly_missing, half_missing, complete, target])


# ---------------------------------------------------------------------
# 4. TARGET LEAKAGE - a column directly derived from the target.
# Purpose: our EXISTING LeakageDetector (correlation-based) must flag
# this. This is the one adversarial case we've already proven against
# (see leakage_detector.py) - included here for completeness of the lab.
# ---------------------------------------------------------------------
def generate_target_leakage(path: str, n_rows: int = 5000):
    rng = _rng()
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["feature_1", "leaky_feature", "target"])
        for _ in range(n_rows):
            target = rng.randint(0, 1)
            leaky_feature = target * 1000 + rng.uniform(-0.5, 0.5)
            writer.writerow([round(rng.uniform(0, 100), 3), round(leaky_feature, 3), target])


# ---------------------------------------------------------------------
# 5. TEMPORAL LEAKAGE - a feature only populated AFTER the outcome is
# known (e.g. a "resolution_time" that only exists for resolved cases).
# Purpose: KNOWN GAP. We do not yet have a temporal-leakage detector -
# our LeakageDetector only checks numeric correlation, and this leak is
# structural (conditional presence of data), not a correlation pattern
# a simple Pearson correlation would necessarily catch. This dataset is
# a placeholder for a future TemporalLeakageDetector.
# ---------------------------------------------------------------------
def generate_temporal_leakage(path: str, n_rows: int = 5000):
    rng = _rng()
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["feature_1", "event_time", "resolution_time", "target"])
        for i in range(n_rows):
            target = rng.randint(0, 1)
            event_time = i  # simple increasing "time" proxy
            # THE LEAK: resolution_time is only ever filled in when
            # target == 1 - a model could learn "resolution_time present
            # -> target=1" even though that information wouldn't exist
            # yet at prediction time in a real deployment.
            resolution_time = event_time + rng.randint(1, 100) if target == 1 else ""
            writer.writerow([round(rng.uniform(0, 100), 3), event_time, resolution_time, target])


# ---------------------------------------------------------------------
# 6. DUPLICATE ENTITIES - the same entity appears multiple times with
# near-identical data, which risks the same entity ending up in both
# train and test splits (a form of leakage via split contamination).
# Purpose: KNOWN GAP. We do not yet have a duplicate-entity/split
# overlap detector. This dataset exists for that future component.
# ---------------------------------------------------------------------
def generate_duplicate_entities(path: str, n_rows: int = 5000, n_unique_entities: int = 500):
    rng = _rng()
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["entity_id", "feature_1", "target"])
        for _ in range(n_rows):
            # Each entity_id repeats ~10 times on average (5000/500) -
            # a real duplicate-entity detector should notice this.
            entity_id = rng.randint(0, n_unique_entities - 1)
            writer.writerow([entity_id, round(rng.uniform(0, 1), 3), rng.randint(0, 1)])


# ---------------------------------------------------------------------
# 7. LARGE DATASET (chunked generation) - proves we can generate (and
# later, process) data far too large to build as one in-memory list.
# Default n_rows is intentionally smaller than the master plan's "10M+"
# for practicality on a laptop - the MECHANISM (writing row-by-row,
# never holding the full dataset in memory) is identical at any scale;
# only the parameter changes. Pass a larger n_rows to genuinely test
# the 10M+ scenario if disk/time allow.
# ---------------------------------------------------------------------
def generate_large_dataset(path: str, n_rows: int = 2_000_000):
    rng = _rng()
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["feature_1", "feature_2", "target"])
        # Writing row-by-row via the csv writer - at no point do we hold
        # more than one row in memory. This is what makes it safe to
        # scale n_rows up to the real 10M+ target without changing code.
        for _ in range(n_rows):
            writer.writerow([round(rng.uniform(0, 1), 4), round(rng.uniform(0, 1), 4), rng.randint(0, 1)])


# ---------------------------------------------------------------------
# 8. CORRUPT SCHEMA - inconsistent types within a column, and malformed
# rows (wrong field count). Purpose: KNOWN GAP. Our current loader/
# profiler assume well-formed CSVs - this dataset will likely cause
# pandas to raise a parsing error or silently coerce types in surprising
# ways. This is intentional: it EXPOSES the gap rather than hiding it.
# A future SchemaValidator should catch this before pandas ever sees it.
# ---------------------------------------------------------------------
def generate_corrupt_schema(path: str, n_rows: int = 1000):
    rng = _rng()
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["numeric_col", "category_col", "target"])
        for i in range(n_rows):
            # Every 20th row: inject a non-numeric value into what should
            # be a purely numeric column - simulates real-world dirty data
            # (e.g. a sensor logging "ERROR" instead of a reading).
            if i % 20 == 0:
                numeric_col = "N/A"
            else:
                numeric_col = round(rng.uniform(0, 100), 3)
            writer.writerow([numeric_col, rng.choice(["A", "B", "C"]), rng.randint(0, 1)])


# ---------------------------------------------------------------------
# 9. HIGH-CARDINALITY CATEGORICAL - a categorical column with many
# distinct values (e.g. simulating product SKUs or user-agent strings),
# but NOT unique enough to be an identifier.
# Purpose: SchemaDetector should classify this as
# CATEGORICAL_HIGH_CARDINALITY, not IDENTIFIER and not
# CATEGORICAL_LOW_CARDINALITY - a real test of the middle bucket.
# ---------------------------------------------------------------------
def generate_high_cardinality_categorical(path: str, n_rows: int = 5000):
    rng = _rng()
    # Deliberately fewer unique tokens than rows, so values repeat -
    # this keeps unique_ratio below the IDENTIFIER threshold (0.95)
    # while still being clearly "high cardinality" relative to a normal
    # low-cardinality categorical like a 3-value country code.
    n_unique_tokens = int(n_rows * 0.6)
    tokens = ["".join(rng.choices(string.ascii_uppercase, k=6)) for _ in range(n_unique_tokens)]

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["product_code", "feature_1", "target"])
        for _ in range(n_rows):
            writer.writerow([rng.choice(tokens), round(rng.uniform(0, 1), 3), rng.randint(0, 1)])


# ---------------------------------------------------------------------
# 10. TEXT-HEAVY - a column containing genuine free-form sentences.
# Purpose: SchemaDetector's TEXT role (avg string length > 50 chars)
# should correctly fire here, distinguishing this from a categorical
# label column.
# ---------------------------------------------------------------------
def generate_text_heavy(path: str, n_rows: int = 2000):
    rng = _rng()
    sample_sentences = [
        "The customer reported an issue with their recent order and requested a refund.",
        "Shipment was delayed due to weather conditions in the regional distribution center.",
        "Product arrived damaged and the packaging showed clear signs of mishandling in transit.",
        "Customer service resolved the billing discrepancy after reviewing the account history.",
        "The item description did not match what was received, prompting a return request.",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["review_text", "rating", "target"])
        for _ in range(n_rows):
            writer.writerow([rng.choice(sample_sentences), rng.randint(1, 5), rng.randint(0, 1)])


# ---------------------------------------------------------------------
# Registry of all 10 generators - used by the validation runner so we
# don't have to hand-list every dataset in two places.
# ---------------------------------------------------------------------
ALL_GENERATORS = {
    "01_normal": generate_normal,
    "02_severe_imbalance": generate_severe_imbalance,
    "03_missing_heavy": generate_missing_heavy,
    "04_target_leakage": generate_target_leakage,
    "05_temporal_leakage": generate_temporal_leakage,
    "06_duplicate_entities": generate_duplicate_entities,
    "07_large_dataset": generate_large_dataset,
    "08_corrupt_schema": generate_corrupt_schema,
    "09_high_cardinality_categorical": generate_high_cardinality_categorical,
    "10_text_heavy": generate_text_heavy,
}


if __name__ == "__main__":
    import os

    output_dir = "data_raw/synthetic_lab"
    os.makedirs(output_dir, exist_ok=True)

    for dataset_name, generator_fn in ALL_GENERATORS.items():
        path = os.path.join(output_dir, f"{dataset_name}.csv")

        # The large dataset gets a SMALLER default here in the demo run,
        # purely so running the full lab doesn't take excessive time -
        # the function itself supports the true 10M+ scale via its
        # n_rows parameter, as documented above.
        if dataset_name == "07_large_dataset":
            generator_fn(path, n_rows=200_000)
        else:
            generator_fn(path)

        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"Generated {dataset_name}.csv ({size_mb:.2f} MB)")

    print(f"\nAll 10 synthetic lab datasets written to: {output_dir}/")