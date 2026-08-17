# AURELIA - Week 1, Step 3: Connecting Mission to Dataset via a Registry
# Save as: D:\AURELIA\domain\registry.py
#
# This file assumes mission.py and dataset.py are saved in the same
# domain/ folder, since it imports from them.

from __future__ import annotations

from domain.dataset import Dataset
from domain.mission import Mission, ResourceBudget


class DatasetNotFoundError(Exception):
    """Raised when a Mission tries to reference a Dataset that doesn't exist."""
    pass


class DatasetRegistry:
    """
    The single source of truth for 'which Datasets exist'.
    Right now this is just an in-memory dict - later this becomes a real
    database table. The INTERFACE (register / get / exists) stays the same
    even when the storage underneath changes - that's the point of a registry.
    """

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
    objective: str,
    dataset_id: str,
    budget: ResourceBudget,
    constraints: list[str],
) -> Mission:
    """
    The RULE lives here, not inside the Mission model itself:
    a Mission can only be created if its dataset_id points to a
    Dataset that has actually been registered.
    """
    if not registry.exists(dataset_id):
        raise DatasetNotFoundError(
            f"Cannot create Mission: dataset_id={dataset_id} is not registered"
        )

    return Mission(
        objective=objective,
        dataset_ref=dataset_id,
        budget=budget,
        constraints=constraints,
    )


if __name__ == "__main__":
    from domain.dataset import DatasetFormat

    registry = DatasetRegistry()

    # Register a real dataset first
    d = Dataset(
        name="large_dataset",
        format=DatasetFormat.PARQUET,
        storage_path="/data/large_dataset.parquet",
    )
    registry.register(d)
    print(f"Registered dataset: {d.id}\n")

    # This should SUCCEED - dataset_id is real
    m = create_mission(
        registry=registry,
        objective="Improve minority-class F1",
        dataset_id=d.id,
        budget=ResourceBudget(max_minutes=240, max_gpu_hours=4.0),
        constraints=["No external data", "No leakage", "Fully reproducible"],
    )
    print("Mission created successfully:")
    print(m.model_dump_json(indent=2))
    print()

    # This should FAIL - dataset_id does not exist
    print("Now trying to create a Mission with a FAKE dataset_id...")
    try:
        create_mission(
            registry=registry,
            objective="This should fail",
            dataset_id="DATASET-doesnotexist",
            budget=ResourceBudget(max_minutes=60, max_gpu_hours=1.0),
            constraints=[],
        )
    except DatasetNotFoundError as e:
        print(f"Correctly rejected: {e}")