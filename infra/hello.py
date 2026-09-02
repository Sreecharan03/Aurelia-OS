import modal

# Step 1: Define the App - this groups our functions together
app = modal.App("aurelia-hello-world")

# Step 2: Define a Function - the @app.function() decorator is what makes
# this run REMOTELY on Modal instead of on your local machine
@app.function()
def hello_from_modal():
    import socket
    import platform

    hostname = socket.gethostname()
    system_info = platform.platform()

    return {
        "message": "Hello from a remote Modal container!",
        "hostname": hostname,
        "system": system_info,
    }

# Step 3: The local entrypoint - this is what runs on YOUR machine
# when you type `modal run hello.py`. It calls the remote function
# and prints what comes back.
@app.local_entrypoint()
def main():
    print("Calling the remote function on Modal...")
    result = hello_from_modal.remote()
    print("Result received back locally:")
    print(result)