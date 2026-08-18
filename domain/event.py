# AURELIA - Week 1, Step 7: Event Sourcing
# Save as: D:\AURELIA\domain\event.py

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """
    The vocabulary of things that can happen in AURELIA.
    This list will grow as we build more of the system - for now it only
    covers the domain models we've already built (Mission through Evidence).
    """
    MISSION_CREATED = "MISSION_CREATED"
    DATASET_REGISTERED = "DATASET_REGISTERED"
    HYPOTHESIS_CREATED = "HYPOTHESIS_CREATED"
    HYPOTHESIS_PRUNED = "HYPOTHESIS_PRUNED"
    EXPERIMENT_CREATED = "EXPERIMENT_CREATED"
    EXPERIMENT_STARTED = "EXPERIMENT_STARTED"
    EXPERIMENT_FAILED = "EXPERIMENT_FAILED"
    EXPERIMENT_COMPLETED = "EXPERIMENT_COMPLETED"
    EVIDENCE_RECORDED = "EVIDENCE_RECORDED"


class Event(BaseModel):
    """
    An IMMUTABLE record that something happened. Once created, an Event
    is never edited or deleted - if something needs to change, a NEW event
    is appended instead. This is what "append-only" means in practice.
    """
    id: str = Field(default_factory=lambda: f"EVT-{uuid4().hex[:8]}")
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Which Mission this event belongs to - lets us replay events for
    # ONE mission at a time, rather than the entire system's history.
    mission_id: str

    # The actual data of the event - kept generic (a plain dict) because
    # different event types carry different payloads (an EXPERIMENT_STARTED
    # event carries different data than a HYPOTHESIS_PRUNED event).
    payload: dict[str, Any] = Field(default_factory=dict)


class EventStore:
    """
    The append-only log itself. Right now this is just an in-memory list -
    later this becomes a real persisted log (e.g. a Postgres table or a
    file). The INTERFACE (append / get_events) stays the same when that
    happens - same pattern as DatasetRegistry.
    """

    def __init__(self):
        self._events: list[Event] = []

    def append(self, event: Event) -> None:
        self._events.append(event)

    def get_events(self, mission_id: str | None = None) -> list[Event]:
        if mission_id is None:
            return list(self._events)
        return [e for e in self._events if e.mission_id == mission_id]


def replay_experiment_statuses(events: list[Event]) -> dict[str, str]:
    """
    A REPLAY FUNCTION: reconstructs current state purely from the event log.
    This is the actual proof of the concept - given ONLY a sequence of
    events (not any stored "current state"), rebuild what the status of
    every experiment is right now.

    This one small function is what "crash recovery" is built on: if the
    process died, we don't trust any in-memory variable - we replay the
    events from the log and rebuild the truth.
    """
    experiment_status: dict[str, str] = {}

    # Events are processed IN ORDER - order matters, because a later
    # event overrides the state implied by an earlier one.
    for event in sorted(events, key=lambda e: e.timestamp):
        if event.event_type == EventType.EXPERIMENT_CREATED:
            experiment_status[event.payload["experiment_id"]] = "CREATED"
        elif event.event_type == EventType.EXPERIMENT_STARTED:
            experiment_status[event.payload["experiment_id"]] = "RUNNING"
        elif event.event_type == EventType.EXPERIMENT_FAILED:
            experiment_status[event.payload["experiment_id"]] = "FAILED"
        elif event.event_type == EventType.EXPERIMENT_COMPLETED:
            experiment_status[event.payload["experiment_id"]] = "COMPLETED"

    return experiment_status


if __name__ == "__main__":
    # Quick manual check - run with: python domain/event.py
    store = EventStore()
    mission_id = "MISSION-d7a2435b"

    # Simulate a sequence of things happening over time, in order,
    # exactly as they would during a real Mission run.
    store.append(Event(
        event_type=EventType.MISSION_CREATED,
        mission_id=mission_id,
        payload={"objective": "Improve minority-class F1"},
    ))

    store.append(Event(
        event_type=EventType.EXPERIMENT_CREATED,
        mission_id=mission_id,
        payload={"experiment_id": "EXP-990f881b", "hypothesis_id": "HYP-c6935cda"},
    ))

    store.append(Event(
        event_type=EventType.EXPERIMENT_STARTED,
        mission_id=mission_id,
        payload={"experiment_id": "EXP-990f881b"},
    ))

    # Simulate a SECOND experiment that fails, to prove replay handles
    # multiple independent experiments correctly.
    store.append(Event(
        event_type=EventType.EXPERIMENT_CREATED,
        mission_id=mission_id,
        payload={"experiment_id": "EXP-11112222", "hypothesis_id": "HYP-c6935cda"},
    ))
    store.append(Event(
        event_type=EventType.EXPERIMENT_STARTED,
        mission_id=mission_id,
        payload={"experiment_id": "EXP-11112222"},
    ))
    store.append(Event(
        event_type=EventType.EXPERIMENT_FAILED,
        mission_id=mission_id,
        payload={"experiment_id": "EXP-11112222", "reason": "OOM"},
    ))

    # The first experiment eventually completes
    store.append(Event(
        event_type=EventType.EXPERIMENT_COMPLETED,
        mission_id=mission_id,
        payload={"experiment_id": "EXP-990f881b", "result_metric": 0.851},
    ))

    print(f"Total events logged: {len(store.get_events())}\n")

    # THE ACTUAL PROOF: reconstruct experiment statuses purely from events,
    # as if we had just crashed and restarted with nothing but this log.
    reconstructed = replay_experiment_statuses(store.get_events(mission_id))

    print("Reconstructed experiment statuses (from replay only):")
    for exp_id, status in reconstructed.items():
        print(f"  {exp_id}: {status}")