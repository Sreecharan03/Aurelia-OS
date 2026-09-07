# AURELIA - Week 2, Step 8: ResourceEstimator
# Save as: D:\AURELIA\ingestion\resource_estimator.py
#
# Estimates the RAM an experiment against a dataset will plausibly need.
# IMPORTANT HONESTY NOTE: this is an ESTIMATE, not a guarantee. Real
# memory usage during training depends on the model, feature encoding,
# and libraries used - none of which this component knows about. Its
# job is to give a defensible STARTING BUDGET, not a precise number.
# This distinction is reflected directly in the output fields below -
# we never claim more precision than we actually have.

from __future__ import annotations
import pandas as pd
from pydantic import BaseModel


class ResourceEstimate(BaseModel):
    """
    Every field name is deliberately explicit about what it actually is -
    a MEASURED sample footprint vs an EXTRAPOLATED full-dataset estimate -
    so nobody downstream mistakes an estimate for a measurement.
    """
    file_size_mb: float

    sample_row_count: int
    measured_sample_memory_mb: float          # ACTUALLY measured, not guessed

    full_row_count: int
    extrapolated_full_memory_mb: float        # derived from the sample, not measured directly

    # Real-world training usage is consistently higher than just holding
    # the raw DataFrame (copies, encoding, intermediate arrays). This
    # margin is an explicit, named assumption - not hidden inside a
    # formula - so it can be examined and tuned later with real data.
    safety_margin_multiplier: float
    recommended_ram_gb: float


class ResourceEstimator:
    """
    Loads a SMALL sample of the real dataset, measures its actual memory
    footprint using pandas' own memory accounting, then extrapolates
    linearly to the full row count. This is far more honest than
    estimating from file-size-on-disk alone, since in-memory
    representation (especially for object/string columns) can be
    significantly larger than the file's bytes on disk.
    """

    # In-memory DataFrames are typically 1.5x-3x larger than the raw file
    # size for numeric-heavy data, and can be much larger for text-heavy
    # data due to Python string object overhead. We apply an additional
    # margin ON TOP of the measured extrapolation to account for what
    # happens DURING an experiment (feature encoding, train/test splits,
    # intermediate arrays existing simultaneously) - none of which is
    # captured by just measuring a static DataFrame's footprint.
    SAFETY_MARGIN_MULTIPLIER = 3.0

    # Sampling too few rows makes the memory-per-row estimate noisy
    # (small samples are dominated by fixed overhead, not the actual
    # per-row cost). This is a floor, not a hard cap - if the full
    # dataset has fewer rows than this, we just use all of it.
    MIN_SAMPLE_ROWS = 1000

    def estimate(self, file_path: str, full_row_count: int) -> ResourceEstimate:
        import os

        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)

        # EDGE CASE: if the full dataset is smaller than our sample floor,
        # just read the whole thing - sampling more rows than exist is
        # meaningless and pandas would just return everything anyway,
        # but being explicit here avoids relying on that implicit behavior.
        sample_size = min(self.MIN_SAMPLE_ROWS, full_row_count)

        sample_df = pd.read_csv(file_path, nrows=sample_size)
        actual_sample_rows = len(sample_df)

        # EDGE CASE: an empty or near-empty file. Without this guard,
        # we'd divide by zero when computing per-row memory below.
        if actual_sample_rows == 0:
            raise ValueError(f"Cannot estimate resources: '{file_path}' produced 0 sample rows")

        # deep=True forces pandas to measure ACTUAL object memory (e.g.
        # real string content), not just pointers - without this,
        # object/string columns would be wildly underestimated.
        sample_memory_bytes = sample_df.memory_usage(deep=True).sum()
        sample_memory_mb = sample_memory_bytes / (1024 * 1024)

        memory_per_row_mb = sample_memory_mb / actual_sample_rows
        extrapolated_full_memory_mb = memory_per_row_mb * full_row_count

        recommended_ram_mb = extrapolated_full_memory_mb * self.SAFETY_MARGIN_MULTIPLIER
        recommended_ram_gb = round(recommended_ram_mb / 1024, 2)

        # EDGE CASE: for very small datasets, the calculation above could
        # recommend an unrealistically tiny budget (e.g. 0.05 GB), which
        # would be a bad experiment budget in practice - no real system
        # runs comfortably on a fraction of a GB. Enforce a sane floor.
        MIN_RECOMMENDED_RAM_GB = 1.0
        recommended_ram_gb = max(recommended_ram_gb, MIN_RECOMMENDED_RAM_GB)

        return ResourceEstimate(
            file_size_mb=round(file_size_mb, 3),
            sample_row_count=actual_sample_rows,
            measured_sample_memory_mb=round(sample_memory_mb, 3),
            full_row_count=full_row_count,
            extrapolated_full_memory_mb=round(extrapolated_full_memory_mb, 2),
            safety_margin_multiplier=self.SAFETY_MARGIN_MULTIPLIER,
            recommended_ram_gb=recommended_ram_gb,
        )


if __name__ == "__main__":
    estimator = ResourceEstimator()

    # Real dataset - we already know its true row count from the profiler
    # (284807), so we pass that in rather than re-reading the whole file
    # just to count rows (that would defeat the purpose of sampling).
    result = estimator.estimate("data_raw/creditcard.csv", full_row_count=284807)

    print(f"File size on disk: {result.file_size_mb} MB")
    print(f"Sample: {result.sample_row_count} rows measured at "
          f"{result.measured_sample_memory_mb} MB (actual, deep memory measurement)")
    print(f"Extrapolated full dataset ({result.full_row_count} rows): "
          f"{result.extrapolated_full_memory_mb} MB")
    print(f"Safety margin applied: {result.safety_margin_multiplier}x "
          f"(accounts for training-time overhead, not just static storage)")
    print(f"\nRecommended RAM budget: {result.recommended_ram_gb} GB")