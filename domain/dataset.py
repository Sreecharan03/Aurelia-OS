# AURELIA - Week 1, Step 2: Dataset domain model

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class DatasetFormat(str, Enum):
    CSV = "CSV"
    PARQUET = "PARQUET"
    JSONL = "JSONL"
    SQL = "SQL"


class DatasetStatus(str, Enum):
    REGISTERED = "REGISTERED"
    PROFILING = "PROFILING"
    PROFILED = "PROFILED"
    REJECTED = "REJECTED"  # e.g. failed leakage/schema checks


class Dataset(BaseModel):
    """
    Represents ONE immutable version of a dataset.
    If the underlying file changes, that becomes a NEW Dataset (new version),
    never an edit to this one - this is what "immutable snapshot" means
    from the original plan.
    """
    id: str = Field(default_factory=lambda: f"DATASET-{uuid4().hex[:8]}")
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)

    name: str = Field(..., description="Human-readable dataset name")
    format: DatasetFormat

    # storage_path is intentionally generic right now - once we build the
    # Modal Volume integration, this will point to a path inside a Volume.
    storage_path: str = Field(..., description="Path to the dataset file in storage")

    # content_hash lets us later verify "is this really the same data
    # as when we last profiled it" - important for reproducibility.
    content_hash: Optional[str] = Field(
        None, description="Hash of the dataset content, filled in after upload"
    )

    row_count: Optional[int] = None
    column_count: Optional[int] = None

    status: DatasetStatus = DatasetStatus.REGISTERED


if __name__ == "__main__":
    # Quick manual check - run with: python domain/dataset.py
    d = Dataset(
        name="large_dataset",
        format=DatasetFormat.PARQUET,
        storage_path="/data/large_dataset.parquet",
    )
    print(d.model_dump_json(indent=2))