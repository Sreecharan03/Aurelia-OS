# AURELIA - Week 2, Step 3: Register the REAL dataset using our Week 1 Dataset model
# Save as: D:\AURELIA\ingestion\register_real_dataset.py
#
# This connects three things we've built separately until now:
# 1. The Dataset domain model (Week 1)
# 2. The DatasetRegistry (Week 1)
# 3. The real file now sitting in the Modal Volume (Week 2)

import hashlib
from domain.dataset import Dataset, DatasetFormat, DatasetStatus
from domain.registry import DatasetRegistry


def compute_file_hash(local_path: str) -> str:
    """
    Computes a SHA-256 hash of the file's actual bytes. Read in chunks
    instead of loading the whole 144MB file into memory at once - this
    is the same "don't just load everything naively" principle from
    our DatasetLoader work, applied here too.
    """
    sha256 = hashlib.sha256()
    with open(local_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


if __name__ == "__main__":
    # We hash from the LOCAL copy (in data_raw/) since it's identical to
    # what we uploaded - computing the hash remotely on Modal is a later
    # optimization, not needed to prove the concept right now.
    local_path = "data_raw/creditcard.csv"

    print("Computing SHA-256 hash of the real dataset file...")
    file_hash = compute_file_hash(local_path)
    print(f"Hash: {file_hash}\n")

    dataset = Dataset(
        name="creditcard_fraud",
        format=DatasetFormat.CSV,
        storage_path="/data/creditcard.csv",  # the real path inside the Modal Volume
        content_hash=file_hash,
        row_count=284807,   # known from the Kaggle dataset description
        column_count=31,
        status=DatasetStatus.REGISTERED,
    )

    registry = DatasetRegistry()
    registry.register(dataset)

    print("Registered real Dataset:")
    print(dataset.model_dump_json(indent=2))

    # Prove the registry actually holds it
    retrieved = registry.get(dataset.id)
    print(f"\nConfirmed retrievable from registry: {retrieved.id == dataset.id}")