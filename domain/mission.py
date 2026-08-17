# AURELIA - Week 1, Step 1: Project structure + first domain model
#
# Recommended folder structure (create these folders in D:\AURELIA):
#
# AURELIA/
# ├── domain/          <- Pydantic models (Mission, Dataset, Hypothesis, etc.)
# ├── docs/             <- hld.md, architecture.md, etc.
# ├── infra/            <- Modal app definitions, Volumes, Images
# ├── tests/            <- tests for each module
# └── README.md
#
# Save this file as: D:\AURELIA\domain\mission.py

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MissionStatus(str, Enum):
    """
    Explicit state machine for a Mission.
    No hidden states - every possible status is listed here.
    """
    CREATED = "CREATED"
    PROFILING = "PROFILING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ResourceBudget(BaseModel):
    """
    What compute resources this Mission is allowed to consume.
    """
    max_minutes: int = Field(..., description="Wall-clock budget in minutes")
    max_gpu_hours: float = Field(..., description="Total GPU-hours allowed")
    max_ram_gb: Optional[int] = Field(None, description="RAM ceiling in GB")


class Mission(BaseModel):
    """
    The top-level object: one research objective + dataset + constraints.
    Everything else (hypotheses, experiments, evidence) hangs off a Mission.
    """
    id: str = Field(default_factory=lambda: f"MISSION-{uuid4().hex[:8]}")
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)

    objective: str = Field(..., description="Plain-language research goal")
    dataset_ref: str = Field(..., description="Reference to the dataset in storage")

    budget: ResourceBudget
    constraints: list[str] = Field(default_factory=list)

    status: MissionStatus = MissionStatus.CREATED


if __name__ == "__main__":
    # Quick manual check - run with: python domain/mission.py
    m = Mission(
        objective="Improve minority-class F1",
        dataset_ref="large_dataset.parquet",
        budget=ResourceBudget(max_minutes=240, max_gpu_hours=4.0),
        constraints=["No external data", "No leakage", "Fully reproducible"],
    )
    print(m.model_dump_json(indent=2))