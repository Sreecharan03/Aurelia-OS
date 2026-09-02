import modal

app = modal.App("aurelia-gpu-check")

# The gpu="T4" parameter tells Modal: attach one T4 GPU to the container
# that runs this function. Without this line, the function runs on CPU only.
@app.function(gpu="T4")
def check_gpu():
    import subprocess

    # nvidia-smi is a standard tool that reports GPU info if a GPU is present
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv"],
        capture_output=True,
        text=True,
    )

    return {
        "gpu_info": result.stdout.strip(),
        "error": result.stderr.strip() if result.returncode != 0 else None,
    }

@app.local_entrypoint()
def main():
    print("Requesting a GPU-attached container on Modal...")
    result = check_gpu.remote()
    print("Result received back locally:")
    print(result)