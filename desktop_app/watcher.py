import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from multiprocessing import Process, Queue


# Custom event handler class for monitoring file creation
class FileCreatedHandler(FileSystemEventHandler):
    def __init__(self, script, queue):
        # Initialize with the script to run and the queue for inter-process communication
        self.script_to_run = script
        self.queue = queue

    def on_created(self, event):
        # Triggered when a file is created in the monitored directory
        if not event.is_directory:  # Ignore directories
            print(f"New file detected: {event.src_path}")
            self.queue.put(event.src_path)  # Put the file path into the queue


# Worker function to process files
def worker(queue, script):
    while True:
        file_path = queue.get()  # Retrieve file path from the queue
        if file_path is None:  # Sentinel value to exit the loop
            break
        print(f"Processing file: {file_path}")
        # Run the specified script with the file path as an argument
        subprocess.run(['python', script, file_path])


# Main execution block
if __name__ == "__main__":
    directory_to_watch = "desktop_app/detections"  # Directory to monitor
    script_to_run = "desktop_app/movement_analysis.py"  # Script to run on new files

    queue = Queue()  # Create a queue for communication between processes
    event_handler = FileCreatedHandler(script_to_run, queue)  # Create the event handler
    observer = Observer()  # Create an Observer to monitor the directory
    observer.schedule(event_handler, directory_to_watch, recursive=False)  # Schedule the event handler

    # Create and start a worker process for processing files
    process = Process(target=worker, args=(queue, script_to_run))
    process.start()

    # Start the Observer to begin monitoring the directory
    observer.start()
    print(f"Monitoring directory: {directory_to_watch}")

    try:
        # Keep the main process alive to allow continuous monitoring
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Handle keyboard interrupt to stop monitoring gracefully
        observer.stop()
        print("Stopping monitoring...")

    # Send sentinel value to the worker process to terminate it
    queue.put(None)
    process.join()  # Wait for the worker process to finish

    # Wait for the Observer to finish any pending operations
    observer.join()
