# AURELIA - Week 2, Step 4b: DatasetProfiler running ON MODAL, against the Volume
# Save as: D:\AURELIA\infra\profiler_modal.py
#
# This wraps the SAME profiling logic from ingestion/profiler.py, but runs
# it remotely on Modal, reading directly from the Volume - your laptop's
# CPU/RAM is never touched by the actual data processing.

import modal

app = modal.App("aurelia-profiler")

volume = modal.Volume.from_name("aurelia-datasets", create_if_missing=True)
VOLUME_MOUNT_PATH = "/data"

# pandas isn't installed locally in our minimal setup, but the REMOTE
# container needs it - so we define an Image with it included.
image = modal.Image.debian_slim().pip_install("pandas", "pydantic")


@app.function(image=image, volumes={VOLUME_MOUNT_PATH: volume})
def profile_dataset(filename: str, target_column: str):
    import pandas as pd

    file_path = f"{VOLUME_MOUNT_PATH}/{filename}"
    df = pd.read_csv(file_path)

    row_count = len(df)
    column_count = len(df.columns)

    missing_counts = df.isnull().sum().to_dict()
    missing_counts = {k: int(v) for k, v in missing_counts.items()}

    class_counts_raw = df[target_column].value_counts().to_dict()
    class_counts = {str(k): int(v) for k, v in class_counts_raw.items()}
    minority_count = min(class_counts.values())
    class_balance_ratio = round((minority_count / row_count) * 100, 4)

    return {
        "row_count": row_count,
        "column_count": column_count,
        "class_counts": class_counts,
        "class_balance_ratio": class_balance_ratio,
        "columns_with_missing_values": [k for k, v in missing_counts.items() if v > 0] or None,
    }


@app.local_entrypoint()
def main():
    print("Profiling runs entirely on Modal - reading directly from the Volume...\n")
    result = profile_dataset.remote("creditcard.csv", "Class")

    print(f"Row count: {result['row_count']}")
    print(f"Column count: {result['column_count']}")
    print(f"Class counts: {result['class_counts']}")
    print(f"Class balance ratio (minority %): {result['class_balance_ratio']}")
    print(f"Columns with missing values: {result['columns_with_missing_values']}")