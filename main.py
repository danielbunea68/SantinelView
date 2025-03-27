import subprocess
import sys

if __name__ == "__main__":
    # List of script paths to be executed concurrently
    scripts = ['api/app.py', 'desktop_app/main.py', 'web_app/app.py', 'desktop_app/watcher.py']

    processes = []  # Initialize an empty list to keep track of process objects

    # Loop through each script and start it as a new process
    for script in scripts:
        # Use Popen to start each script as a subprocess
        process = subprocess.Popen(
            ["python", script],  # Command to run the script
            stderr=sys.stderr,  # Redirect standard error to the parent process's stderr
            stdout=sys.stdout  # Redirect standard output to the parent process's stdout
        )
        processes.append(process)  # Add the process object to the list

    # Loop through the list of processes to monitor their completion
    for process in processes:
        stdout, stderr = process.communicate()  # Wait for the process to complete and capture output

        # Check if the process completed successfully
        if process.returncode == 0:
            print(f"{process.args[1]} completed successfully.")  # Print success message
            print(stdout.decode())  # Print the captured standard output
        else:
            print(f"Error running {process.args[1]}.")  # Print error message
            print(stderr.decode())  # Print the captured standard error
