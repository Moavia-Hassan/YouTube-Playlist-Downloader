import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QProgressBar, QComboBox, QFileDialog, QMessageBox, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import yt_dlp

class DownloadWorker(QThread):
    progress = pyqtSignal(float)
    status = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, url, save_path, format_id, num_videos):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.format_id = format_id
        self.num_videos = num_videos

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            if 'total_bytes' in d:
                percentage = (d['downloaded_bytes'] / d['total_bytes']) * 100
                self.progress.emit(percentage)
                self.status.emit(f"Downloading: {percentage:.1f}%")
            elif 'downloaded_bytes' in d:
                self.status.emit(f"Downloading... ({d['downloaded_bytes'] / 1024 / 1024:.1f} MB)")
        elif d['status'] == 'finished':
            self.status.emit('Processing completed file...')

    def run(self):
        try:
            ydl_opts = {
                'format': self.format_id,
                'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'noplaylist': True if self.num_videos == 1 else False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('YouTube Downloader')
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QLineEdit, QComboBox {
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                font-size: 14px;
            }
            QProgressBar::chunk {
                background-color: #007BFF;
            }
            QLabel {
                font-size: 14px;
            }
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
                padding: 10px;
            }
        """)

        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # URL input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Enter YouTube URL (video or playlist)')
        url_layout.addWidget(QLabel('URL:'))
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        # Format selection
        format_layout = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(['Best Quality (Video + Audio)', 'HD 1080p', 'HD 720p', 'SD 480p', 'SD 360p', 'Audio Only (MP3)'])
        format_layout.addWidget(QLabel('Format:'))
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # Save location
        save_layout = QHBoxLayout()
        self.save_path = QLineEdit()
        self.save_path.setPlaceholderText('Select save location')
        self.save_path.setText(os.path.expanduser("~/Downloads"))
        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(self.browse_location)
        save_layout.addWidget(QLabel('Save to:'))
        save_layout.addWidget(self.save_path)
        save_layout.addWidget(browse_btn)
        layout.addLayout(save_layout)

        # Number of videos
        num_videos_layout = QHBoxLayout()
        self.num_videos_input = QLineEdit()
        self.num_videos_input.setPlaceholderText('Enter number of videos to download (for playlists)')
        num_videos_layout.addWidget(QLabel('Number of videos:'))
        num_videos_layout.addWidget(self.num_videos_input)
        layout.addLayout(num_videos_layout)

        # Download button
        self.download_btn = QPushButton('Download')
        self.download_btn.clicked.connect(self.start_download)
        layout.addWidget(self.download_btn)

        # Progress bar and status
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel('Ready')
        layout.addWidget(self.status_label)

        # Detailed status
        self.detailed_status = QTextEdit()
        self.detailed_status.setReadOnly(True)
        layout.addWidget(self.detailed_status)

        self.setMinimumSize(600, 400)
        self.center_window()

    def center_window(self):
        qr = self.frameGeometry()
        cp = QApplication.desktop().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def browse_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Location")
        if folder:
            self.save_path.setText(folder)

    def check_ffmpeg_installed(self):
        from shutil import which
        return which("ffmpeg") is not None

    def start_download(self):
        if not self.check_ffmpeg_installed():
            QMessageBox.critical(self, 'Error', 'ffmpeg is not installed. Please install ffmpeg to proceed.')
            return

        url = self.url_input.text().strip()
        save_path = self.save_path.text().strip()
        num_videos = self.num_videos_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, 'Error', 'Please enter a URL')
            return
        if not save_path:
            QMessageBox.warning(self, 'Error', 'Please select a save location')
            return
        if not num_videos.isdigit() or int(num_videos) <= 0:
            QMessageBox.warning(self, 'Error', 'Please enter a valid number of videos')
            return

        format_id = self.get_format_id()
        
        self.download_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText('Starting download...')
        self.detailed_status.clear()
        
        self.worker = DownloadWorker(url, save_path, format_id, int(num_videos))
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.download_finished)
        self.worker.error.connect(self.download_error)
        self.worker.start()

    def get_format_id(self):
        format_map = {
            0: 'bestvideo+bestaudio/best',
            1: 'bestvideo[height<=1080]+bestaudio/best',
            2: 'bestvideo[height<=720]+bestaudio/best',
            3: 'bestvideo[height<=480]+bestaudio/best',
            4: 'bestvideo[height<=360]+bestaudio/best',
            5: 'bestaudio/best'
        }
        return format_map.get(self.format_combo.currentIndex(), 'bestvideo+bestaudio/best')

    def update_progress(self, value):
        self.progress_bar.setValue(int(value))

    def update_status(self, status):
        self.status_label.setText(status)
        self.detailed_status.append(status)

    def download_finished(self):
        self.download_btn.setEnabled(True)
        self.status_label.setText('Download completed successfully!')
        self.detailed_status.append('Download completed successfully!')
        QMessageBox.information(self, 'Success', 'Download completed successfully!')

    def download_error(self, error):
        self.download_btn.setEnabled(True)
        self.status_label.setText('Error occurred during download')
        self.detailed_status.append(f'Error: {error}')
        QMessageBox.critical(self, 'Error', f'Download failed: {error}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())