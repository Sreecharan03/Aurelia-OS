# AURELIA - Week 2, Step 6: DatasetVersioner
# Save as: D:\AURELIA\ingestion\versioner.py
#
# This is the "git commit" equivalent for datasets: same name + same
# content_hash -> no-op (nothing changed). Same name + DIFFERENT
# content_hash -> a new version is created, linked to what it replaced.

from __future__ import annotations
from domain.dataset import Dataset, DatasetFormat, DatasetStatus


class DatasetVersioner:
    """
    Tracks dataset versions BY NAME. Works alongside DatasetRegistry:
    the Registry answers "does this exact Dataset ID exist" - the
    Versioner answers "is this content NEW for this dataset name, or
    have we already seen it".
    """

    def __init__(self):
        # Maps a dataset NAME -> the latest known Dataset record for it.
        # This is separate from DatasetRegistry's id-based lookup on purpose:
        # a name can have MULTIPLE Dataset ids over time (one per version),
        # but only one is "latest" at any moment.
        self._latest_by_name: dict[str, Dataset] = {}

    def register_or_version(
        self,
        name: str,
        format: DatasetFormat,
        storage_path: str,
        content_hash: str,
        row_count: int | None = None,
        column_count: int | None = None,
    ) -> tuple[Dataset, bool]:
        """
        Returns (dataset, is_new_version).
        is_new_version=False means this was a no-op (identical content
        already registered) - the EXISTING Dataset is returned, not a
        new one, so no duplicate records get created for the same data.
        """
        existing = self._latest_by_name.get(name)

        if existing is not None and existing.content_hash == content_hash:
            # Same name, same content - nothing changed. No-op.
            return existing, False

        # Either this name has never been seen, OR the content changed.
        new_version_number = (existing.version + 1) if existing else 1

        dataset = Dataset(
            name=name,
            format=format,
            storage_path=storage_path,
            content_hash=content_hash,
            row_count=row_count,
            column_count=column_count,
            status=DatasetStatus.REGISTERED,
        )
        # Manually set the version number, since Dataset defaults to 1 -
        # we need it to reflect its position in THIS name's history.
        dataset.version = new_version_number

        self._latest_by_name[name] = dataset
        return dataset, True

    def get_latest(self, name: str) -> Dataset | None:
        return self._latest_by_name.get(name)


if __name__ == "__main__":
    # Quick manual check - run with: python -m ingestion.versioner
    versioner = DatasetVersioner()

    # First registration - should be a NEW version (v1)
    d1, is_new1 = versioner.register_or_version(
        name="creditcard_fraud",
        format=DatasetFormat.CSV,
        storage_path="/data/creditcard.csv",
        content_hash="76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89",
        row_count=284807,
        column_count=31,
    )
    print(f"First registration -> is_new_version={is_new1}, version={d1.version}, id={d1.id}")

    # Re-registering the EXACT SAME content - should be a NO-OP
    d2, is_new2 = versioner.register_or_version(
        name="creditcard_fraud",
        format=DatasetFormat.CSV,
        storage_path="/data/creditcard.csv",
        content_hash="76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89",
        row_count=284807,
        column_count=31,
    )
    print(f"Re-registering same content -> is_new_version={is_new2}, version={d2.version}, "
          f"same id as before={d2.id == d1.id}")

    # Registering with DIFFERENT content (simulated new hash) - should be v2
    d3, is_new3 = versioner.register_or_version(
        name="creditcard_fraud",
        format=DatasetFormat.CSV,
        storage_path="/data/creditcard_updated.csv",
        content_hash="DIFFERENT_HASH_SIMULATING_CHANGED_DATA",
        row_count=290000,
        column_count=31,
    )
    print(f"Different content -> is_new_version={is_new3}, version={d3.version}, "
          f"different id from v1={d3.id != d1.id}")