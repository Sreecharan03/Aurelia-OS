# AURELIA - Week 1, Step 5: Experiment domain model
# Save as: D:\AURELIA\domain\experiment.py

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ExperimentStatus(str, Enum):
    """
    State machine from the master plan:
    CREATED -> VALIDATING -> QUEUED -> RUNNING -> COMPLETED
    with a separate failure branch:
    RUNNING -> FAILED -> CLASSIFIED -> REPAIRING -> RETRYING
    Terminal states: COMPLETED, FAILED_FINAL, CANCELLED, INVALID, RESOURCE_INFEASIBLE
    """
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"

    FAILED = "FAILED"
    CLASSIFIED = "CLASSIFIED"
    REPAIRING = "REPAIRING"
    RETRYING = "RETRYING"

    # Terminal states
    FAILED_FINAL = "FAILED_FINAL"
    CANCELLED = "CANCELLED"
    INVALID = "INVALID"
    RESOURCE_INFEASIBLE = "RESOURCE_INFEASIBLE"


class ExperimentBudget(BaseModel):
    max_minutes: int
    gpu_count: int = 0
    ram_gb: int


class ExperimentContract(BaseModel):
    """
    Everything an Experiment MUST declare before it's considered valid.
    From the master plan: 'The experiment is invalid if any are missing.'
    This is why these are required fields, not optional ones.
    """
    dataset_id: str
    features: list[str]
    target: str
    split_strategy: str = Field(..., description="e.g. 'random_80_20', 'time_based'")
    model_name: str = Field(..., description="e.g. 'LightGBM', 'CatBoost'")
    hyperparameters: dict = Field(default_factory=dict)
    seed: int
    metric: str = Field(..., description="e.g. 'f1_minority'")


class Experiment(BaseModel):
    """
    The concrete, executable test of ONE Hypothesis.
    An Experiment without a valid ExperimentContract should never be allowed
    to run - that validation happens outside this model, in the Validator
    we'll build later. This model just guarantees the SHAPE is correct.
    """
    id: str = Field(default_factory=lambda: f"EXP-{uuid4().hex[:8]}")
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)

    mission_id: str
    hypothesis_id: str = Field(..., description="Which Hypothesis this experiment tests")

    contract: ExperimentContract
    budget: ExperimentBudget

    status: ExperimentStatus = ExperimentStatus.CREATED

    # Filled in only after the experiment actually runs
    result_metric: Optional[float] = None
    artifact_paths: list[str] = Field(default_factory=list)

    # Reproducibility fields - from the master plan's "REPRODUCIBILITY" section
    code_hash: Optional[str] = None
    environment_hash: Optional[str] = None


if __name__ == "__main__":
    # Quick manual check - run with: python domain/experiment.py
    contract = ExperimentContract(
        dataset_id="DATASET-aeb2a0b1",
        features=["feature_1", "feature_2", "feature_3"],
        target="label",
        split_strategy="random_80_20",
        model_name="CatBoost",
        hyperparameters={"iterations": 500, "depth": 6},
        seed=42,
        metric="f1_minority",
    )

    exp = Experiment(
        mission_id="MISSION-d7a2435b",
        hypothesis_id="HYP-c6935cda",
        contract=contract,
        budget=ExperimentBudget(max_minutes=18, gpu_count=1, ram_gb=16),
    )

    print(exp.model_dump_json(indent=2))