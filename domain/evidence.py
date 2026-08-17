# AURELIA - Week 1, Step 6: Evidence domain model
# Save as: D:\AURELIA\domain\evidence.py

from __future__ import annotations
from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class EvidenceVerdict(str, Enum):
    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    INCONCLUSIVE = "INCONCLUSIVE"


class Evidence(BaseModel):
    """
    The formal link between an Experiment's result and the Hypothesis
    it was testing. A Hypothesis should NEVER move to VALIDATED or REFUTED
    without at least one Evidence record justifying that transition -
    this model is what makes that justification explicit and auditable.
    """
    id: str = Field(default_factory=lambda: f"EVD-{uuid4().hex[:8]}")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    hypothesis_id: str
    experiment_id: str = Field(..., description="Which Experiment produced this evidence")

    metric_observed: float
    metric_baseline: float

    verdict: EvidenceVerdict

    # Statistical backing - from the master plan's "STATISTICAL VALIDATION"
    # and "MULTI-SEED REPLICATION" sections. Not every piece of evidence
    # will have all of these filled in immediately, hence Optional-style
    # defaults, but the shape exists so we can enforce it later.
    seed_count: int = Field(1, description="How many seeds this result was replicated across")
    std_dev: float | None = Field(None, description="Standard deviation across seed runs")
    confidence_interval: tuple[float, float] | None = None

    notes: str = Field("", description="Free-text justification for the verdict")


if __name__ == "__main__":
    # Quick manual check - run with: python domain/evidence.py
    e = Evidence(
        hypothesis_id="HYP-c6935cda",
        experiment_id="EXP-990f881b",
        metric_observed=0.851,
        metric_baseline=0.821,
        verdict=EvidenceVerdict.SUPPORTS,
        seed_count=3,
        std_dev=0.006,
        confidence_interval=(0.842, 0.860),
        notes="Improvement consistent across 3 seeds, within expected range (0.84-0.86)",
    )
    print(e.model_dump_json(indent=2))