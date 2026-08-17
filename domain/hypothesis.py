# AURELIA - Week 1, Step 4: Hypothesis domain model
# Save as: D:\AURELIA\domain\hypothesis.py

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class HypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SELECTED = "SELECTED"      # chosen for experimentation
    TESTING = "TESTING"        # experiment(s) currently running against it
    VALIDATED = "VALIDATED"    # evidence supported it
    REFUTED = "REFUTED"        # evidence contradicted it
    PRUNED = "PRUNED"          # discarded without testing (e.g. depended on a refuted hypothesis)


class Hypothesis(BaseModel):
    """
    A structured, falsifiable research claim - NOT a vague idea.
    Every field here exists specifically to prevent "maybe CatBoost works better"
    from being an acceptable hypothesis. It forces a baseline, an expected
    outcome, and a confidence level BEFORE any experiment is run.
    """
    id: str = Field(default_factory=lambda: f"HYP-{uuid4().hex[:8]}")
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)

    mission_id: str = Field(..., description="Which Mission this hypothesis belongs to")

    claim: str = Field(..., description="The specific, testable claim being made")
    rationale: str = Field(..., description="Why we believe this claim might be true")

    baseline_metric: float = Field(..., description="Current known metric value")
    expected_metric_min: float = Field(..., description="Lower bound of expected improvement")
    expected_metric_max: float = Field(..., description="Upper bound of expected improvement")

    confidence: float = Field(..., ge=0.0, le=1.0, description="Self-assessed confidence, 0 to 1")
    estimated_cost_minutes: int = Field(..., description="Estimated compute cost to test this")

    # Graph relationships - these are just IDs for now (references to other
    # Hypotheses). We are NOT building the actual graph engine yet - just
    # making sure the model can express these relationships when we do.
    derived_from: Optional[str] = Field(None, description="Hypothesis ID this was derived from")
    depends_on: list[str] = Field(default_factory=list, description="Hypothesis IDs this depends on")

    status: HypothesisStatus = HypothesisStatus.PROPOSED


if __name__ == "__main__":
    # Quick manual check - run with: python domain/hypothesis.py
    h = Hypothesis(
        mission_id="MISSION-d7a2435b",
        claim="CatBoost will outperform LightGBM on minority F1 due to high-cardinality categorical features",
        rationale="CatBoost has native handling for high-cardinality categoricals via ordered target statistics",
        baseline_metric=0.821,
        expected_metric_min=0.84,
        expected_metric_max=0.86,
        confidence=0.68,
        estimated_cost_minutes=18,
    )
    print(h.model_dump_json(indent=2))