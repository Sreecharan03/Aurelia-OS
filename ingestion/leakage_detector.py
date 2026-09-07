# AURELIA - Week 2, Step 5b: Deterministic Leakage Detector
# Save as: D:\AURELIA\ingestion\leakage_detector.py

from __future__ import annotations
import pandas as pd
from pydantic import BaseModel


class LeakageSignal(BaseModel):
    column: str
    correlation_with_target: float
    reason: str


class LeakageReport(BaseModel):
    target_column: str
    signals: list[LeakageSignal]

    @property
    def has_leakage(self) -> bool:
        return len(self.signals) > 0


class LeakageDetector:
    """
    Deterministic, statistics-only leakage detection - no LLM involved.
    This is intentionally narrow right now: it only checks for
    target-derived columns via correlation. The master plan lists many
    more leakage types (temporal, group, train/test overlap) - those are
    separate detectors we'll add later, not crammed into this one.
    """

    # Correlation above this threshold is treated as a near-certain leak.
    # 0.95 is deliberately strict - real, legitimate features rarely
    # correlate this perfectly with the target.
    CORRELATION_THRESHOLD = 0.95

    def detect(self, file_path: str, target_column: str) -> LeakageReport:
        df = pd.read_csv(file_path)

        if target_column not in df.columns:
            raise ValueError(f"target_column '{target_column}' not found in dataset")

        signals: list[LeakageSignal] = []

        numeric_df = df.select_dtypes(include="number")

        for column in numeric_df.columns:
            if column == target_column:
                continue

            correlation = numeric_df[column].corr(numeric_df[target_column])

            if pd.isna(correlation):
                continue

            if abs(correlation) >= self.CORRELATION_THRESHOLD:
                signals.append(LeakageSignal(
                    column=column,
                    correlation_with_target=round(float(correlation), 4),
                    reason=(
                        f"Correlation {correlation:.4f} with target exceeds "
                        f"threshold {self.CORRELATION_THRESHOLD} - likely "
                        f"target-derived (leakage)"
                    ),
                ))

        return LeakageReport(target_column=target_column, signals=signals)


if __name__ == "__main__":
    from ingestion.synthetic_leaky_data import generate_leaky_dataset

    detector = LeakageDetector()

    # TEST 1: the KNOWN-BAD case - should DEFINITELY flag feature_LEAKY
    print("=" * 60)
    print("TEST 1: Synthetic dataset with DELIBERATE leakage")
    print("=" * 60)
    generate_leaky_dataset("data_raw/synthetic_leaky.csv")
    leaky_report = detector.detect("data_raw/synthetic_leaky.csv", target_column="target")

    print(f"\nHas leakage detected: {leaky_report.has_leakage}")
    for signal in leaky_report.signals:
        print(f"  FLAGGED: {signal.column} -> {signal.reason}")

    # TEST 2: the KNOWN-CLEAN case - should NOT flag anything (or very little)
    print("\n" + "=" * 60)
    print("TEST 2: Real credit card fraud dataset (should be clean)")
    print("=" * 60)
    clean_report = detector.detect("data_raw/creditcard.csv", target_column="Class")

    print(f"\nHas leakage detected: {clean_report.has_leakage}")
    if clean_report.signals:
        for signal in clean_report.signals:
            print(f"  FLAGGED: {signal.column} -> {signal.reason}")
    else:
        print("  No columns flagged - correctly stayed silent on clean data.")