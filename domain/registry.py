# AURELIA - Week 1, Step 8: Wiring events into the real flow
# This REPLACES your existing domain/registry.py

from __future__ import annotations

from domain.dataset import Dataset
from domain.mission import Mission, ResourceBudget
from domain.event import Event, EventStore, EventType


class DatasetNotFoundError(Exception):
    """Raised when a Mission tries to reference a Dataset that doesn't exist."""
    pass


class DatasetRegistry:
    def __init__(self):
        self._datasets: dict[str, Dataset] = {}

    def register(self, dataset: Dataset) -> None:
        self._datasets[dataset.id] = dataset

    def get(self, dataset_id: str) -> Dataset:
        if dataset_id not in self._datasets:
            raise DatasetNotFoundError(f"No dataset registered with id={dataset_id}")
        return self._datasets[dataset_id]

    def exists(self, dataset_id: str) -> bool:
        return dataset_id in self._datasets


def create_mission(
    registry: DatasetRegistry,
    event_store: EventStore,
    objective: str,
    dataset_id: str,
    budget: ResourceBudget,
    constraints: list[str],
) -> Mission:
    """
    Same validation rule as before - PLUS it now automatically appends
    a MISSION_CREATED event to the event_store. The caller never has to
    remember to log this manually - it's baked into the function that
    actually creates the Mission. This is the pattern we'll repeat for
    every state-changing operation in the system.
    """
    if not registry.exists(dataset_id):
        raise DatasetNotFoundError(
            f"Cannot create Mission: dataset_id={dataset_id} is not registered"
        )

    mission = Mission(
        objective=objective,
        dataset_ref=dataset_id,
        budget=budget,
        constraints=constraints,
    )

    # The event is emitted HERE, as part of creation - not as a separate
    # manual step the caller could forget to do.
    event_store.append(Event(
        event_type=EventType.MISSION_CREATED,
        mission_id=mission.id,
        payload={
            "objective": mission.objective,
            "dataset_ref": mission.dataset_ref,
        },
    ))

    return mission


if __name__ == "__main__":
    from domain.dataset import DatasetFormat

    registry = DatasetRegistry()
    event_store = EventStore()

    d = Dataset(
        name="large_dataset",
        format=DatasetFormat.PARQUET,
        storage_path="/data/large_dataset.parquet",
    )
    registry.register(d)
    print(f"Registered dataset: {d.id}\n")

    m = create_mission(
        registry=registry,
        event_store=event_store,
        objective="Improve minority-class F1",
        dataset_id=d.id,
        budget=ResourceBudget(max_minutes=240, max_gpu_hours=4.0),
        constraints=["No external data", "No leakage", "Fully reproducible"],
    )
    print(f"Mission created: {m.id}\n")

    # THE PROOF: check the event store WITHOUT ever looking at the
    # mission object itself - the event should exist automatically.
    events = event_store.get_events(mission_id=m.id)
    print(f"Events automatically recorded for this mission: {len(events)}")
    for e in events:
        print(f"  {e.event_type} -> {e.payload}")