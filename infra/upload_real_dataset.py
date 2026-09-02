# AURELIA - Week 2, Step 2b: Upload the REAL fraud dataset to a Modal Volume
# Save as: D:\AURELIA\infra\upload_real_dataset.py

import modal

app = modal.App("aurelia-upload-real-dataset")

volume = modal.Volume.from_name("aurelia-datasets", create_if_missing=True)
VOLUME_MOUNT_PATH = "/data"

# This mounts your LOCAL data_raw folder so Modal can access the file
# during the upload call. This only happens once, for the upload itself -
# after this, the file lives in the Volume permanently, not locally.
LOCAL_FILE_PATH = "./data_raw/creditcard.csv"


@app.function(volumes={VOLUME_MOUNT_PATH: volume})
def upload_file(file_bytes: bytes, filename: str):
    remote_path = f"{VOLUME_MOUNT_PATH}/{filename}"
    with open(remote_path, "wb") as f:
        f.write(file_bytes)
    volume.commit()
    return {"remote_path": remote_path, "size_bytes": len(file_bytes)}


@app.function(volumes={VOLUME_MOUNT_PATH: volume})
def verify_file(filename: str):
    import os
    remote_path = f"{VOLUME_MOUNT_PATH}/{filename}"
    size = os.path.getsize(remote_path)

    # Read just the header + first data row to prove it's real, readable data
    with open(remote_path, "r") as f:
        header = f.readline().strip()
        first_row = f.readline().strip()

    return {
        "remote_path": remote_path,
        "size_bytes": size,
        "size_mb": round(size / (1024 * 1024), 2),
        "header": header,
        "first_row": first_row,
    }


@app.local_entrypoint()
def main():
    print(f"Reading local file: {LOCAL_FILE_PATH}")
    with open(LOCAL_FILE_PATH, "rb") as f:
        file_bytes = f.read()
    print(f"Read {len(file_bytes) / (1024*1024):.2f} MB locally. Uploading to Modal Volume...\n")

    upload_result = upload_file.remote(file_bytes, "creditcard.csv")
    print(f"Upload complete: {upload_result}\n")

    print("Verifying from a SEPARATE remote call (different container)...")
    verify_result = verify_file.remote("creditcard.csv")
    print(f"Verified: {verify_result['size_mb']} MB on the Volume")
    print(f"Header: {verify_result['header'][:100]}...")
    print(f"First data row: {verify_result['first_row'][:100]}...")