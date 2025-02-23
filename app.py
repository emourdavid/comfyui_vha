import os
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog,
                               QHBoxLayout, QVBoxLayout, QLabel, QWidget, QTextEdit)
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeySequence, QShortcut
from PySide6.QtCore import Qt
import subprocess

class VideoFrameExtractor(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Video Frame Extractor")
        self.setGeometry(100, 100, 600, 400)
        self.setAcceptDrops(True)

        self.selected_path = ""
        self.main_layout = QVBoxLayout()

        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.main_layout.addWidget(self.log_display)

        # Buttons layout
        self.button_layout = QHBoxLayout()

        # Button to select file or folder
        self.select_button = QPushButton("Select File/Folder")
        self.select_button.setMinimumSize(150, 40)
        self.select_button.clicked.connect(self.select_file_or_folder)
        self.button_layout.addWidget(self.select_button)

        # Button to run processing
        self.run_button = QPushButton("Run (Ctrl+Enter)")
        self.run_button.setMinimumSize(150, 40)
        self.run_button.clicked.connect(self.process_videos)
        self.button_layout.addWidget(self.run_button)

        # Button to extract the last frame
        self.last_frame_button = QPushButton("Get Last Frame")
        self.last_frame_button.setMinimumSize(150, 40)
        self.last_frame_button.clicked.connect(self.get_last_frame)
        self.button_layout.addWidget(self.last_frame_button)

        # Button to open frames folder
        self.open_folder_button = QPushButton("Open Frames Folder")
        self.open_folder_button.setMinimumSize(150, 40)
        self.open_folder_button.clicked.connect(self.open_frames_folder)
        self.button_layout.addWidget(self.open_folder_button)

        # Add buttons layout to main layout
        self.main_layout.addLayout(self.button_layout)

        # Label for selected file or folder
        self.path_label = QLabel("Drag and drop or select a file/folder.")
        self.path_label.setWordWrap(True)
        self.main_layout.addWidget(self.path_label)

        # Shortcut for run button
        self.shortcut = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self.shortcut.activated.connect(self.process_videos)

        # Main widget setup
        widget = QWidget()
        widget.setLayout(self.main_layout)
        self.setCentralWidget(widget)

    def log(self, message):
        self.log_display.append(message)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            self.selected_path = urls[0].toLocalFile()
            self.path_label.setText(f"Selected: {self.selected_path}")

    def select_file_or_folder(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        path = QFileDialog.getExistingDirectory(self, "Select Folder") or QFileDialog.getOpenFileName(self, "Select File", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")[0]
        if path:
            self.selected_path = path
            self.path_label.setText(f"Selected: {self.selected_path}")

    def process_videos(self):
        if not self.selected_path:
            self.path_label.setText("Error: No file or folder selected.")
            return

        # Read configuration from config.txt
        config_file = "config.txt"
        if not os.path.exists(config_file):
            with open(config_file, "w") as f:
                f.write("-r 1")  # Default: 1 frame per second

        with open(config_file, "r") as f:
            ffmpeg_options = f.read().strip()

        # Process videos
        if os.path.isfile(self.selected_path):
            self.extract_frames(self.selected_path, ffmpeg_options)
        elif os.path.isdir(self.selected_path):
            for root, _, files in os.walk(self.selected_path):
                for file in files:
                    if file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                        video_path = os.path.join(root, file)
                        self.extract_frames(video_path, ffmpeg_options)

        self.path_label.setText("Processing completed.")

    def extract_frames(self, video_path, ffmpeg_options):
        base_name = os.path.basename(video_path).split('.')[0]
        output_dir = os.path.join(os.path.dirname(video_path), f"frames_{base_name}")
        os.makedirs(output_dir, exist_ok=True)

        output_pattern = os.path.join(output_dir, base_name + "_%04d.png")
        command = ["ffmpeg", "-y", "-i", video_path, "-q:v", "2"] + ffmpeg_options.split() + [output_pattern]

        try:
            subprocess.run(command, check=True)
            self.log(f"Frames extracted for {video_path}")
        except subprocess.CalledProcessError as e:
            error_message = f"Error processing {video_path}: {e}"
            self.log(error_message)
            self.path_label.setText(error_message)

    def get_last_frame(self):
        if not self.selected_path or not os.path.isfile(self.selected_path):
            self.path_label.setText("Error: No file selected.")
            return

        base_name = os.path.basename(self.selected_path).split('.')[0]
        output_dir = os.path.join(os.path.dirname(self.selected_path), f"frames_{base_name}")
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(output_dir, base_name + "_last_frame.png")

        # Get the total number of frames in the video
        try:
            frame_count_cmd = ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", self.selected_path]
            frame_count_result = subprocess.run(frame_count_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            total_frames = int(frame_count_result.stdout.strip())
            self.log(f"Total frames: {total_frames}")

            # Extract the exact last frame
            command = ["ffmpeg", "-y", "-i", self.selected_path, "-vf", f"select='eq(n,{total_frames - 1})'", "-vsync", "vfr", "-q:v", "2", "-frames:v", "1", output_file]
            subprocess.run(command, check=True)
            success_message = f"Last frame saved to: {output_file}"
            self.log(success_message)
            self.path_label.setText(success_message)
        except (subprocess.CalledProcessError, ValueError) as e:
            error_message = f"Error extracting last frame: {e}"
            self.log(error_message)
            self.path_label.setText(error_message)

    def open_frames_folder(self):
        if self.selected_path:
            base_name = os.path.basename(self.selected_path).split('.')[0]
            output_dir = os.path.join(os.path.dirname(self.selected_path), f"frames_{base_name}")
            if os.path.exists(output_dir):
                os.startfile(output_dir)  # Open folder in file explorer
            else:
                self.path_label.setText("Frames folder does not exist.")
        else:
            self.path_label.setText("No file or folder selected.")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = VideoFrameExtractor()
    window.show()

    sys.exit(app.exec())
