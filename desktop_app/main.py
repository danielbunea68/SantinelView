import sys
import os
import cv2
import time
import datetime
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QComboBox
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
import webbrowser
import shutil
import os


def detect_movement(frame, mog2):
    """
    Detects movement in the frame using MOG2 background subtractor and morphological operations.

    Parameters:
    frame (numpy.ndarray): The current video frame.
    mog2 (cv2.BackgroundSubtractorMOG2): The background subtractor object.

    Returns:
    tuple: A boolean indicating if movement is detected, the foreground mask, and the contours.
    """
    # Apply background subtraction to get the foreground mask
    fg_mask = mog2.apply(frame)
    # Define a kernel for morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    # Close small holes in the foreground
    closing = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
    # Remove noise from the foreground
    opening = cv2.morphologyEx(closing, cv2.MORPH_OPEN, kernel)
    # Find contours in the foreground mask
    contours, _ = cv2.findContours(opening, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Return whether movement is detected, the mask, and the contours
    return len(contours) > 0, fg_mask, contours


def start_recording(frame, fourcc):
    """
    Starts recording by initializing the VideoWriter object.

    Parameters:
    frame (numpy.ndarray): The current video frame.
    fourcc (cv2.VideoWriter_fourcc): The codec for video recording.

    Returns:
    tuple: The VideoWriter object, the start time of the recording, and the filename.
    """
    # Ensure the directory for saving videos exists
    if not os.path.exists('desktop_app/temp'):
        os.makedirs('desktop_app/temp')
    # Create a timestamped filename for the video
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join('desktop_app/temp', f'{timestamp}.mp4')
    # Initialize the VideoWriter object for recording
    out = cv2.VideoWriter(filename, fourcc, 20.0, (frame.shape[1], frame.shape[0]))
    # Return the VideoWriter, start time, and filename
    return out, time.time(), filename


def calculate_fps(start_time, frame_count):
    """
    Calculates the frames per second (FPS).

    Parameters:
    start_time (float): The start time of the FPS calculation.
    frame_count (int): The number of frames processed.

    Returns:
    float: The calculated FPS.
    """
    # Calculate the elapsed time
    elapsed_time = time.time() - start_time
    # Calculate FPS based on the number of frames and elapsed time
    return frame_count / elapsed_time if elapsed_time > 0 else 0


def non_max_suppression(boxes, overlap_thresh):
    """
    Perform non-max suppression to suppress overlapping bounding boxes.

    Parameters:
    boxes (list): List of bounding boxes.
    overlapThresh (float): Overlap threshold.

    Returns:
    list: List of indices of bounding boxes to keep.
    """
    if len(boxes) == 0:
        return []
    if boxes.dtype.kind == "i":
        boxes = boxes.astype("float")

    pick = []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = y2
    idxs = idxs.argsort()

    while len(idxs) > 0:
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        overlap = (w * h) / area[idxs[:last]]
        idxs = np.delete(idxs, np.concatenate(([last], np.where(overlap > overlap_thresh)[0])))

    return pick


class VideoThread(QThread):
    update_frame = pyqtSignal(QImage)

    def __init__(self):
        super().__init__()
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.display_frame)
        self.detecting = False
        self.recording = False
        self.mog2 = cv2.createBackgroundSubtractorMOG2(500, 16, True)
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = None
        self.movement_counter = 0
        self.recording_start_time = None
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.recording_path = ""

    def start_camera(self, camera_index=0):
        """
        Starts the camera and initializes video capture.

        Parameters:
        camera_index (int): Index of the camera to use (default is 0).
        """
        if self.cap is not None and self.cap.isOpened():
            return
        # Open the video capture with the specified camera index
        self.cap = cv2.VideoCapture(2)
        if not self.cap.isOpened():
            print("Error: Could not open camera.")
            return
        # Start a timer to periodically update the frame display
        self.timer.start(30)

    def stop_camera(self):
        """
        Stops the camera and releases resources.
        """
        self.timer.stop()
        if self.cap:
            self.cap.release()
        if self.out:
            self.out.release()
        # Reset flags and counters
        self.cap = None
        self.out = None
        self.detecting = False
        self.recording = False
        self.movement_counter = 0

    def toggle_detection(self):
        """
        Toggles the movement detection on or off.
        """
        self.detecting = not self.detecting
        if not self.detecting:
            if self.recording:
                self.out.release()
            self.recording = False
            self.movement_counter = 0

    def display_frame(self):
        """
        Captures and processes frames from the camera, displaying the video feed and handling detection and recording.
        """
        ret, frame = self.cap.read()
        if not ret:
            return

        self.frame_count += 1

        if self.detecting:
            # Detect movement in the current frame
            detection, fg_mask, contours = detect_movement(frame, self.mog2)
            if detection:
                self.movement_counter += 1
            else:
                self.movement_counter = 0

            # Start recording if movement is detected for more than 30 frames
            if self.movement_counter > 30 and not self.recording:
                self.out, self.recording_start_time, self.recording_path = start_recording(frame, self.fourcc)
                self.recording = True

            if self.recording:
                # Write the frame to the output video file
                self.out.write(frame)
                # Display recording status and elapsed time on the frame
                cv2.putText(frame, "Recording", (40, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1, cv2.LINE_AA)
                cv2.circle(frame, (20, 60), 10, (0, 0, 255), -1)
                elapsed_time = time.time() - self.recording_start_time
                cv2.putText(frame, f'Time: {elapsed_time:.2f}s', (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1,
                            cv2.LINE_AA)
                # Stop recording after 10 seconds
                if time.time() - self.recording_start_time >= 10:
                    self.recording = False
                    self.out.release()
                    # Move the recorded video to the detections folder
                    if not os.path.exists('desktop_app/detections'):
                        os.makedirs('desktop_app/detections')
                    file_name = os.path.basename(self.recording_path)
                    new_path = os.path.join('desktop_app/detections', file_name)
                    shutil.move(self.recording_path, new_path)

            # Calculate and display the current FPS on the frame
            fps = calculate_fps(self.fps_start_time, self.frame_count)
            cv2.putText(frame, f'FPS: {fps:.2f}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

            # Detect and draw bounding boxes around moving objects
            boxes = []
            for contour in contours:
                if cv2.contourArea(contour) > 500:
                    x, y, w, h = cv2.boundingRect(contour)
                    boxes.append([x, y, x + w, y + h])
            if len(boxes) > 0:
                boxes = np.array(boxes)
                pick = non_max_suppression(boxes, 0.3)
                for i in pick:
                    x1, y1, x2, y2 = boxes[i]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Convert the frame from BGR to RGB format for displaying in the GUI
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Convert the RGB image to QImage format
        convert_to_qt_format = QImage(rgb_image.data, rgb_image.shape[1], rgb_image.shape[0], QImage.Format_RGB888)
        # Emit the updated frame to be displayed in the GUI
        self.update_frame.emit(convert_to_qt_format)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set the main window title and size
        self.setWindowTitle("Camera Monitor")
        self.setGeometry(100, 100, 800, 600)

        # Create a label to display the video feed
        self.video_label = QLabel(self)
        self.video_label.setFixedSize(800, 600)

        # Create a dropdown for camera selection (currently supports only one camera)
        self.camera_selector = QComboBox(self)
        self.camera_selector.addItem("Camera 0")

        # Create a button to start/stop movement detection
        self.start_button = QPushButton("Start Detection", self)
        self.start_button.clicked.connect(self.toggle_detection)

        # Create a button to launch a web portal
        self.launch_button = QPushButton("Launch Portal", self)
        self.launch_button.clicked.connect(self.launch_website)

        # Create a vertical layout and add widgets
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.video_label)
        self.layout.addWidget(self.camera_selector)
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.launch_button)

        # Create a container widget and set it as the central widget
        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

        # Initialize the video thread and connect the frame update signal to the image display slot
        self.video_thread = VideoThread()
        self.video_thread.update_frame.connect(self.set_image)
        # Connect camera selection change to the change_camera method
        self.camera_selector.currentIndexChanged.connect(self.change_camera)

    def set_image(self, image):
        """
        Sets the image in the video label.

        Parameters:
        image (QImage): The image to display.
        """
        self.video_label.setPixmap(QPixmap.fromImage(image))

    def toggle_detection(self):
        """
        Toggles the movement detection on or off and updates the button text.
        """
        if self.video_thread.detecting:
            # Stop detection if it's currently running
            self.video_thread.toggle_detection()
            self.start_button.setText("Start Detection")
        else:
            # Start the camera and detection
            self.video_thread.start_camera(self.camera_selector.currentIndex())
            self.video_thread.toggle_detection()
            self.start_button.setText("Stop Detection")

    def change_camera(self, index):
        """
        Changes the camera input if detection is currently running.

        Parameters:
        index (int): The index of the selected camera.
        """
        if self.video_thread.detecting:
            # Stop and restart the camera with the new selection
            self.video_thread.stop_camera()
            self.video_thread.start_camera(index)

    def closeEvent(self, event):
        """
        Handles the event when the main window is closed.

        Parameters:
        event (QCloseEvent): The close event.
        """
        # Ensure the camera is stopped before closing the application
        self.video_thread.stop_camera()
        event.accept()

    def launch_website(self, event):
        """
        Opens the web portal in the default browser.

        Parameters:
        event (QEvent): The event triggering the launch.
        """
        webbrowser.open("http://127.0.0.1:5000/")


if __name__ == "__main__":
    # Initialize the application
    app = QApplication(sys.argv)
    # Create and show the main window
    window = MainWindow()
    window.show()
    # Run the application's event loop
    sys.exit(app.exec_())
