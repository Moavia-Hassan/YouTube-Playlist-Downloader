import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import yt_dlp

class UrlValidator(QThread):
    finished = pyqtSignal(bool, str, int)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        try:
            with yt_dlp.YoutubeDL() as ydl:
                info = ydl.extract_info(self.url, download=False)
                is_playlist = 'entries' in info
                title = info.get('title', '')
                video_count = len(info['entries']) if is_playlist else 1
                self.finished.emit(True, title, video_count)
        except Exception as e:
            self.finished.emit(False, str(e), 0)

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
                'playlistend': self.num_videos if self.num_videos > 1 else None,
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
        self.current_step = 0
        self.video_count = 0
        self.is_playlist = False

    def initUI(self):
        self.setWindowTitle('YouTube Downloader')
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                color: #ffffff;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QLineEdit, QComboBox, QSpinBox {
                padding: 12px;
                background-color: #3b3b3b;
                border: 2px solid #505050;
                border-radius: 6px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #007BFF;
            }
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: #3b3b3b;
                height: 20px;
                text-align: center;
                font-size: 14px;
            }
            QProgressBar::chunk {
                background-color: #007BFF;
                border-radius: 6px;
            }
            QLabel {
                font-size: 14px;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #3b3b3b;
                border: 2px solid #505050;
                border-radius: 6px;
                color: #ffffff;
                font-size: 14px;
                padding: 10px;
            }
        """)

        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(40, 40, 40, 40)

        # Step 1: URL Input
        self.url_widget = QWidget()
        url_layout = QVBoxLayout(self.url_widget)
        
        title_label = QLabel('YouTube Downloader')
        title_label.setStyleSheet('font-size: 24px; font-weight: bold; color: #007BFF; margin-bottom: 20px;')
        url_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        
        url_input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Enter YouTube URL')
        self.validate_btn = QPushButton('Validate URL')
        self.validate_btn.clicked.connect(self.validate_url)
        url_input_layout.addWidget(self.url_input)
        url_input_layout.addWidget(self.validate_btn)
        url_layout.addLayout(url_input_layout)
        
        self.main_layout.addWidget(self.url_widget)

        # Step 2: Video Count (Initially hidden)
        self.count_widget = QWidget()
        self.count_widget.hide()
        count_layout = QVBoxLayout(self.count_widget)
        self.video_info_label = QLabel()
        count_layout.addWidget(self.video_info_label)
        
        self.count_input_layout = QHBoxLayout()
        self.count_input = QSpinBox()
        self.count_input.setMinimum(1)
        self.count_next_btn = QPushButton('Next')
        self.count_next_btn.clicked.connect(self.show_format_selection)
        self.count_input_layout.addWidget(self.count_input)
        self.count_input_layout.addWidget(self.count_next_btn)
        count_layout.addLayout(self.count_input_layout)
        
        self.main_layout.addWidget(self.count_widget)

        # Step 3: Format Selection (Initially hidden)
        self.format_widget = QWidget()
        self.format_widget.hide()
        format_layout = QVBoxLayout(self.format_widget)
        self.format_combo = QComboBox()
        self.format_combo.addItems(['Best Quality (Video + Audio)', 'HD 1080p', 'HD 720p', 
                                  'SD 480p', 'SD 360p', 'Audio Only (MP3)'])
        format_layout.addWidget(QLabel('Select Format:'))
        format_layout.addWidget(self.format_combo)
        
        self.save_path = QLineEdit()
        self.save_path.setText(os.path.expanduser("~/Downloads"))
        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(self.browse_location)
        
        save_layout = QHBoxLayout()
        save_layout.addWidget(self.save_path)
        save_layout.addWidget(browse_btn)
        format_layout.addLayout(save_layout)
        
        self.download_btn = QPushButton('Start Download')
        self.download_btn.clicked.connect(self.start_download)
        format_layout.addWidget(self.download_btn)
        
        self.main_layout.addWidget(self.format_widget)

        # Progress Section (Initially hidden)
        self.progress_widget = QWidget()
        self.progress_widget.hide()
        progress_layout = QVBoxLayout(self.progress_widget)
        
        self.progress_bar = QProgressBar()
        self.status_label = QLabel('Ready')
        self.detailed_status = QTextEdit()
        self.detailed_status.setReadOnly(True)
        self.detailed_status.setMaximumHeight(150)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.detailed_status)
        
        self.main_layout.addWidget(self.progress_widget)

        self.setMinimumSize(800, 600)
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

    def validate_url(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, 'Error', 'Please enter a URL')
            return
            
        self.validate_btn.setEnabled(False)
        self.validate_btn.setText('Validating...')
        self.validator = UrlValidator(url)
        self.validator.finished.connect(self.handle_validation_result)
        self.validator.start()

    def handle_validation_result(self, is_valid, title, count):
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText('Validate URL')
        
        if is_valid:
            self.video_count = count
            self.is_playlist = count > 1
            self.video_info_label.setText(
                f"Found: {title}\n" +
                (f"Playlist with {count} videos" if self.is_playlist else "Single video")
            )
            
            if self.is_playlist:
                self.count_input.setMaximum(count)
                self.count_input.setValue(count)
                self.count_widget.show()
            else:
                self.count_input.setValue(1)
                self.show_format_selection()
        else:
            QMessageBox.warning(self, 'Error', f'Invalid URL: {title}')

    def show_format_selection(self):
        self.format_widget.show()
        self.progress_widget.show()

    def start_download(self):
        if not self.check_ffmpeg_installed():
            QMessageBox.critical(self, 'Error', 'ffmpeg is not installed. Please install ffmpeg to proceed.')
            return

        url = self.url_input.text().strip()
        save_path = self.save_path.text().strip()
        num_videos = self.count_input.value()
        
        if not url:
            QMessageBox.warning(self, 'Error', 'Please enter a URL')
            return
        if not save_path:
            QMessageBox.warning(self, 'Error', 'Please select a save location')
            return

        format_id = self.get_format_id()
        
        self.download_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText('Starting download...')
        self.detailed_status.clear()
        
        self.worker = DownloadWorker(url, save_path, format_id, num_videos)
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