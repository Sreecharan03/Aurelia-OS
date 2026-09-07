# AURELIA - Week 2, Step 7 (CORRECTED): SchemaDetector
# Save as: D:\AURELIA\ingestion\schema_detector.py
#
# Infers the SEMANTIC ROLE of each column (identifier, categorical,
# numerical, datetime, constant, text) - not just its raw pandas dtype.
#
# BUG FIX from first version: the IDENTIFIER rule originally checked
# ONLY unique_ratio, which misclassified continuous float columns (like
# PCA components) as identifiers - because continuous floats are almost
# always near-100% unique just by chance, not because they're IDs.
# Identifiers must now ALSO match an appropriate dtype (integer or
# string/object) - float columns can never be classified as identifiers,
# no matter how unique their values are.

from __future__ import annotations
import warnings
from enum import Enum
import pandas as pd
from pydantic import BaseModel


class ColumnRole(str, Enum):
    CONSTANT = "CONSTANT"                          # only one distinct value
    NEAR_CONSTANT = "NEAR_CONSTANT"                 # one value dominates >=99%
    DATETIME = "DATETIME"                           # parses as a date/time
    IDENTIFIER = "IDENTIFIER"                       # near-unique int/string, likely a row ID
    BINARY = "BINARY"                                # exactly 2 distinct values
    TEXT = "TEXT"                                    # long free-text strings
    CATEGORICAL_LOW_CARDINALITY = "CATEGORICAL_LOW_CARDINALITY"
    CATEGORICAL_HIGH_CARDINALITY = "CATEGORICAL_HIGH_CARDINALITY"
    NUMERICAL = "NUMERICAL"                          # continuous/ordinal numeric feature
    UNKNOWN = "UNKNOWN"                              # fallback - should be rare


class ColumnSchema(BaseModel):
    """
    The full profile of ONE column: its inferred role, plus the raw
    statistics that justified that decision. Evidence is kept alongside
    the verdict on purpose - so a human (or later, the Critic agent) can
    audit WHY a column was classified a certain way, not just trust a
    label with no reasoning attached.
    """
    name: str
    pandas_dtype: str
    role: ColumnRole

    unique_count: int
    unique_ratio: float          # unique_count / total_rows
    dominant_value_ratio: float  # frequency of the single most common value
    null_ratio: float


class DatasetSchema(BaseModel):
    columns: list[ColumnSchema]

    @property
    def identifier_candidates(self) -> list[str]:
        return [c.name for c in self.columns if c.role == ColumnRole.IDENTIFIER]

    @property
    def constant_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.role == ColumnRole.CONSTANT]

    @property
    def near_constant_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.role == ColumnRole.NEAR_CONSTANT]

    @property
    def high_cardinality_categoricals(self) -> list[str]:
        return [c.name for c in self.columns if c.role == ColumnRole.CATEGORICAL_HIGH_CARDINALITY]


class SchemaDetector:
    """
    Deterministic column-role classification. Every threshold below is a
    named constant with a stated reason - nothing is a magic number
    buried in an if-statement.
    """

    NEAR_CONSTANT_THRESHOLD = 0.99

    # Identifier uniqueness threshold - but this ALONE is not sufficient.
    # See _could_be_identifier_dtype() below: dtype must also be
    # integer or object/string. Continuous floats are EXCLUDED entirely,
    # because near-uniqueness is their normal, expected behavior, not
    # evidence of being an ID column.
    IDENTIFIER_UNIQUE_RATIO_THRESHOLD = 0.95

    LOW_CARDINALITY_UNIQUE_RATIO_THRESHOLD = 0.05
    TEXT_AVG_LENGTH_THRESHOLD = 50

    def detect(self, file_path: str) -> DatasetSchema:
        df = pd.read_csv(file_path)
        row_count = len(df)

        if row_count == 0:
            # Edge case: an empty file. Don't silently produce nonsense
            # stats (e.g. division by zero) - fail loudly and clearly.
            raise ValueError(f"Cannot detect schema: '{file_path}' has 0 rows")

        column_schemas: list[ColumnSchema] = []
        for column_name in df.columns:
            column_schemas.append(self._classify_column(df[column_name], column_name, row_count))

        return DatasetSchema(columns=column_schemas)

    def _classify_column(self, series: pd.Series, name: str, row_count: int) -> ColumnSchema:
        unique_count = series.nunique(dropna=True)
        unique_ratio = unique_count / row_count if row_count > 0 else 0.0
        null_ratio = series.isnull().mean()

        value_counts = series.value_counts(normalize=True, dropna=True)
        dominant_value_ratio = float(value_counts.iloc[0]) if len(value_counts) > 0 else 0.0

        pandas_dtype = str(series.dtype)

        # EDGE CASE: a column that is ENTIRELY null. nunique() on an
        # all-null series is 0, which would otherwise fall through every
        # rule below into UNKNOWN with a division-safe but meaningless
        # unique_ratio of 0.0. Call this out explicitly as CONSTANT,
        # since "always missing" is functionally the same problem as
        # "always the same value" for a model - both carry zero signal.
        if unique_count == 0:
            role = ColumnRole.CONSTANT

        # RULE 1: Constant - only one distinct value exists at all.
        elif unique_count <= 1:
            role = ColumnRole.CONSTANT

        # RULE 2: Near-constant - one value dominates almost everything.
        elif dominant_value_ratio >= self.NEAR_CONSTANT_THRESHOLD:
            role = ColumnRole.NEAR_CONSTANT

        # RULE 3: Datetime - attempt a parse; if it succeeds for nearly
        # every non-null value, treat it as a real datetime column.
        elif self._looks_like_datetime(series):
            role = ColumnRole.DATETIME

        # RULE 4: Identifier - requires BOTH high uniqueness AND an
        # appropriate dtype (integer or string/object). This is the
        # fix: a float column can NEVER be classified as an identifier,
        # regardless of its unique_ratio, because continuous numeric
        # data is naturally near-unique and that is not an ID signal.
        elif unique_ratio >= self.IDENTIFIER_UNIQUE_RATIO_THRESHOLD and self._could_be_identifier_dtype(series):
            role = ColumnRole.IDENTIFIER

        # RULE 5: Binary - exactly two distinct values (common for
        # flags and target columns).
        elif unique_count == 2:
            role = ColumnRole.BINARY

        # RULE 6: Text - object dtype with long average string length
        # signals free text rather than a categorical label.
        elif pandas_dtype == "object" and self._avg_string_length(series) > self.TEXT_AVG_LENGTH_THRESHOLD:
            role = ColumnRole.TEXT

        # RULE 7/8: Categorical, split by cardinality.
        elif pandas_dtype == "object" or unique_ratio < self.LOW_CARDINALITY_UNIQUE_RATIO_THRESHOLD:
            if unique_ratio < self.LOW_CARDINALITY_UNIQUE_RATIO_THRESHOLD:
                role = ColumnRole.CATEGORICAL_LOW_CARDINALITY
            else:
                role = ColumnRole.CATEGORICAL_HIGH_CARDINALITY

        # RULE 9: Numerical - the fallback for numeric dtypes that didn't
        # match any special case above. This is where continuous floats
        # (like V1-V28) correctly land now, instead of being misflagged
        # as identifiers.
        elif pd.api.types.is_numeric_dtype(series):
            role = ColumnRole.NUMERICAL

        # RULE 10: Anything else we genuinely can't classify confidently.
        else:
            role = ColumnRole.UNKNOWN

        return ColumnSchema(
            name=name,
            pandas_dtype=pandas_dtype,
            role=role,
            unique_count=int(unique_count),
            unique_ratio=round(float(unique_ratio), 4),
            dominant_value_ratio=round(dominant_value_ratio, 4),
            null_ratio=round(float(null_ratio), 4),
        )

    @staticmethod
    def _could_be_identifier_dtype(series: pd.Series) -> bool:
        """
        Only integer and object/string dtypes are eligible to be
        identifiers. Floats are EXCLUDED on principle: continuous
        numeric values are naturally near-unique, so high uniqueness
        in a float column is expected behavior, not an ID signal.
        """
        kind = series.dtype.kind
        # 'i' = signed int, 'u' = unsigned int, 'O' = object (string/mixed)
        return kind in ("i", "u", "O")

    @staticmethod
    def _looks_like_datetime(series: pd.Series) -> bool:
        if series.dtype != "object":
            return False
        sample = series.dropna().head(50)
        if len(sample) == 0:
            return False
        try:
            # Suppress pandas' "could not infer format" warning - we are
            # DELIBERATELY speculatively parsing many non-date columns
            # here and expect frequent failures; that's not noteworthy.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                parsed = pd.to_datetime(sample, errors="coerce")
            success_ratio = parsed.notna().mean()
            return success_ratio >= 0.9
        except Exception:
            return False

    @staticmethod
    def _avg_string_length(series: pd.Series) -> float:
        non_null = series.dropna().astype(str)
        if len(non_null) == 0:
            return 0.0
        return float(non_null.str.len().mean())


if __name__ == "__main__":
    import csv
    import random

    detector = SchemaDetector()

    # TEST 1: a synthetic file with an OBVIOUS integer ID column AND a
    # continuous float column that is ALSO near-100% unique. This is the
    # exact scenario that exposed the bug - both are highly unique, but
    # only ONE of them should be flagged as an identifier.
    print("=" * 60)
    print("TEST 1: Synthetic dataset - integer ID vs continuous float")
    print("=" * 60)

    random.seed(1)
    with open("data_raw/synthetic_schema_test.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row_id", "category", "continuous_score", "target"])
        for i in range(200):
            writer.writerow([i, random.choice(["A", "B", "C"]), random.uniform(0, 1), random.randint(0, 1)])

    schema = detector.detect("data_raw/synthetic_schema_test.csv")
    for col in schema.columns:
        print(f"  {col.name}: {col.role} (dtype={col.pandas_dtype}, unique_ratio={col.unique_ratio})")
    print(f"\nIdentifier candidates found: {schema.identifier_candidates}")
    print("Expected: ONLY 'row_id' - 'continuous_score' must NOT appear despite being ~100% unique")

    # TEST 2: the real credit card dataset - continuous PCA float columns
    # (V1-V28) must NOT be flagged as identifiers anymore.
    print("\n" + "=" * 60)
    print("TEST 2: Real credit card fraud dataset")
    print("=" * 60)

    real_schema = detector.detect("data_raw/creditcard.csv")
    for col in real_schema.columns[:5]:
        print(f"  {col.name}: {col.role} (dtype={col.pandas_dtype}, unique_ratio={col.unique_ratio})")
    print(f"  ... ({len(real_schema.columns)} columns total)")
    print(f"\nIdentifier candidates found: {real_schema.identifier_candidates}")
    print("Expected: [] - this dataset has no real ID column, and V1-V28 are floats")
    print(f"Constant columns found: {real_schema.constant_columns}")