# AURELIA - Week 2, Step 10: Validate detectors against the Synthetic Data Lab
# Save as: D:\AURELIA\ingestion\validate_lab.py
#
# This is the actual PROOF step. Generating adversarial datasets means
# nothing on its own - this script runs our REAL detectors against them
# and checks whether each one reacts the way it should. Where we have
# NO detector yet for a given adversarial case, that is reported
# explicitly as a gap, not silently skipped.

from ingestion.schema_detector import SchemaDetector, ColumnRole
from ingestion.leakage_detector import LeakageDetector
from ingestion.profiler import DatasetProfiler

LAB_DIR = "data_raw/synthetic_lab"


def check_normal():
    print("[01_normal] Expect: NO leakage, NO identifier false-positives")
    leakage = LeakageDetector().detect(f"{LAB_DIR}/01_normal.csv", target_column="target")
    schema = SchemaDetector().detect(f"{LAB_DIR}/01_normal.csv")
    passed = (not leakage.has_leakage) and (len(schema.identifier_candidates) == 0)
    print(f"  Leakage detected: {leakage.has_leakage} (expected False)")
    print(f"  Identifier false-positives: {schema.identifier_candidates} (expected [])")
    print(f"  RESULT: {'PASS' if passed else 'FAIL'}\n")


def check_severe_imbalance():
    print("[02_severe_imbalance] Expect: DatasetProfiler reports ~1% minority class")
    profile = DatasetProfiler().profile(f"{LAB_DIR}/02_severe_imbalance.csv", target_column="target")
    passed = profile.class_balance_ratio < 5.0  # should be close to 1%, well under 5%
    print(f"  Reported minority class ratio: {profile.class_balance_ratio}% (expected ~1%)")
    print(f"  RESULT: {'PASS' if passed else 'FAIL'}\n")


def check_missing_heavy():
    print("[03_missing_heavy] Expect: DatasetProfiler reports high missing % on 2 columns")
    profile = DatasetProfiler().profile(f"{LAB_DIR}/03_missing_heavy.csv", target_column="target")
    mostly_missing_pct = profile.missing_value_percentages.get("mostly_missing", 0)
    half_missing_pct = profile.missing_value_percentages.get("half_missing", 0)
    passed = mostly_missing_pct > 70 and half_missing_pct > 30
    print(f"  mostly_missing column: {mostly_missing_pct}% missing (expected ~85%)")
    print(f"  half_missing column: {half_missing_pct}% missing (expected ~50%)")
    print(f"  RESULT: {'PASS' if passed else 'FAIL'}\n")


def check_target_leakage():
    print("[04_target_leakage] Expect: LeakageDetector flags 'leaky_feature'")
    leakage = LeakageDetector().detect(f"{LAB_DIR}/04_target_leakage.csv", target_column="target")
    flagged_columns = [s.column for s in leakage.signals]
    passed = "leaky_feature" in flagged_columns
    print(f"  Flagged columns: {flagged_columns} (expected to include 'leaky_feature')")
    print(f"  RESULT: {'PASS' if passed else 'FAIL'}\n")


def check_high_cardinality_categorical():
    print("[09_high_cardinality_categorical] Expect: SchemaDetector classifies "
          "'product_code' as CATEGORICAL_HIGH_CARDINALITY (NOT identifier)")
    schema = SchemaDetector().detect(f"{LAB_DIR}/09_high_cardinality_categorical.csv")
    product_code_col = next(c for c in schema.columns if c.name == "product_code")
    passed = product_code_col.role == ColumnRole.CATEGORICAL_HIGH_CARDINALITY
    print(f"  product_code classified as: {product_code_col.role} "
          f"(unique_ratio={product_code_col.unique_ratio})")
    print(f"  RESULT: {'PASS' if passed else 'FAIL'}\n")


def check_text_heavy():
    print("[10_text_heavy] Expect: SchemaDetector classifies 'review_text' as TEXT")
    schema = SchemaDetector().detect(f"{LAB_DIR}/10_text_heavy.csv")
    review_col = next(c for c in schema.columns if c.name == "review_text")
    passed = review_col.role == ColumnRole.TEXT
    print(f"  review_text classified as: {review_col.role}")
    print(f"  RESULT: {'PASS' if passed else 'FAIL'}\n")


def report_known_gaps():
    print("=" * 60)
    print("KNOWN GAPS - datasets exist, but NO detector exists yet")
    print("=" * 60)
    print("  [05_temporal_leakage]    - no TemporalLeakageDetector built yet")
    print("  [06_duplicate_entities]  - no duplicate-entity/split-overlap detector built yet")
    print("  [08_corrupt_schema]      - no pre-parse SchemaValidator built yet")
    print("  [07_large_dataset]       - generation proven chunked/scalable; large-scale")
    print("                             PROFILING at 10M+ rows not yet load-tested")
    print("These datasets are reserved for future components, not silently ignored.\n")


if __name__ == "__main__":
    print("=" * 60)
    print("SYNTHETIC DATA LAB - Detector Validation")
    print("=" * 60 + "\n")

    check_normal()
    check_severe_imbalance()
    check_missing_heavy()
    check_target_leakage()
    check_high_cardinality_categorical()
    check_text_heavy()

    report_known_gaps()