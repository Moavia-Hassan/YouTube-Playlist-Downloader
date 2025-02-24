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
            ydl_opts = {
                'extract_flat': True,  # Only extract metadata, don't download video info
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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

    def __init__(self, url, save_path, format_id, num_videos, is_playlist=False):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.format_id = format_id
        self.num_videos = num_videos
        self.is_playlist = is_playlist

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
                'noplaylist': not self.is_playlist,
                'playlist_items': f'1-{self.num_videos}' if self.is_playlist else None,
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
                /* Remove transform property as it's not supported */
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
            QComboBox {
                padding: 12px;
                background-color: #3b3b3b;
                border: 2px solid #505050;
                border-radius: 6px;
                color: white;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                width: 0;
                height: 0;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #3b3b3b;
                color: white;
                selection-background-color: #007BFF;
                selection-color: white;
                border: 1px solid #505050;
            }
            QWidget#formatContainer, QWidget#saveContainer {
                background-color: #363636;
                border-radius: 10px;
                padding: 20px;
                margin: 10px;
            }
            QSpinBox {
                min-width: 100px;
                max-width: 150px;
            }
            QFrame.StepContainer {
                background-color: #363636;
                border-radius: 10px;
                padding: 20px;
                margin: 10px;
                border: 1px solid #505050;
            }
            QFrame.StepContainer:hover {
                border: 1px solid #007BFF;
            }
            QLabel.StepTitle {
                font-size: 18px;
                font-weight: bold;
                color: #007BFF;
                padding: 5px 0;
                margin-bottom: 10px;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton#downloadBtn {
                background-color: #28a745;
                font-size: 16px;
                min-width: 200px;
            }
            QPushButton#downloadBtn:hover {
                background-color: #218838;
            }
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: #3b3b3b;
                height: 25px;
                text-align: center;
                font-size: 14px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 6px;
            }
        """)

        # Main widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Title
        title = QLabel('YouTube Downloader')
        title.setStyleSheet('font-size: 24px; font-weight: bold; color: #007BFF;')
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Stack for steps
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # Step 1: URL Input
        url_page = QFrame()
        url_page.setObjectName("step1")
        url_page.setStyleSheet("QFrame#step1 { background-color: transparent; }")
        url_layout = QVBoxLayout(url_page)
        
        url_container = QFrame()
        url_container.setObjectName("urlContainer")
        url_container.setProperty("class", "StepContainer")
        url_container_layout = QVBoxLayout(url_container)
        
        url_label = QLabel('Enter YouTube URL:')
        url_label.setProperty("class", "StepTitle")
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Paste URL here')
        self.url_input.setMinimumHeight(45)
        
        self.validate_btn = QPushButton('Validate URL')
        self.validate_btn.setMinimumHeight(45)
        self.validate_btn.clicked.connect(self.validate_url)
        
        url_container_layout.addWidget(url_label)
        url_container_layout.addWidget(self.url_input)
        url_container_layout.addWidget(self.validate_btn)
        url_layout.addWidget(url_container)
        url_layout.addStretch()
        
        self.stack.addWidget(url_page)

        # Step 2: Playlist Options
        playlist_page = QFrame()
        playlist_page.setObjectName("step2")
        playlist_layout = QVBoxLayout(playlist_page)
        
        playlist_container = QFrame()
        playlist_container.setProperty("class", "StepContainer")
        playlist_container_layout = QVBoxLayout(playlist_container)
        
        self.video_info_label = QLabel()
        self.video_info_label.setProperty("class", "StepTitle")
        self.video_info_label.setWordWrap(True)
        
        count_layout = QHBoxLayout()
        count_label = QLabel("Number of videos to download:")
        self.count_input = QSpinBox()
        self.count_input.setMinimumHeight(45)
        self.count_input.setMinimum(1)
        
        count_layout.addWidget(count_label)
        count_layout.addWidget(self.count_input)
        count_layout.addStretch()
        
        next_btn = QPushButton('Next')
        next_btn.setMinimumHeight(45)
        next_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        
        playlist_container_layout.addWidget(self.video_info_label)
        playlist_container_layout.addLayout(count_layout)
        playlist_container_layout.addWidget(next_btn)
        playlist_layout.addWidget(playlist_container)
        playlist_layout.addStretch()
        
        self.stack.addWidget(playlist_page)

        # Step 3: Download Options
        download_page = QFrame()
        download_page.setObjectName("step3")
        download_layout = QVBoxLayout(download_page)
        
        options_container = QFrame()
        options_container.setProperty("class", "StepContainer")
        options_layout = QVBoxLayout(options_container)
        
        # Format selection
        format_label = QLabel('Select Format:')
        format_label.setProperty("class", "StepTitle")
        self.format_combo = QComboBox()
        self.format_combo.addItems(['Best Quality (Video + Audio)', 'HD 1080p', 'HD 720p', 
                                  'SD 480p', 'SD 360p', 'Audio Only (MP3)'])
        self.format_combo.setMinimumHeight(45)
        
        # Save location
        location_label = QLabel('Save Location:')
        location_label.setProperty("class", "StepTitle")
        location_layout = QHBoxLayout()
        self.save_path = QLineEdit(os.path.expanduser("~/Downloads"))
        self.save_path.setMinimumHeight(45)
        browse_btn = QPushButton('Browse')
        browse_btn.setFixedSize(100, 45)
        browse_btn.clicked.connect(self.browse_location)
        location_layout.addWidget(self.save_path)
        location_layout.addWidget(browse_btn)
        
        self.download_btn = QPushButton('Start Download')
        self.download_btn.setObjectName("downloadBtn")
        self.download_btn.setMinimumHeight(45)
        self.download_btn.clicked.connect(self.start_download)
        
        options_layout.addWidget(format_label)
        options_layout.addWidget(self.format_combo)
        options_layout.addWidget(location_label)
        options_layout.addLayout(location_layout)
        options_layout.addWidget(self.download_btn)
        
        download_layout.addWidget(options_container)
        
        # Progress section
        progress_container = QFrame()
        progress_container.setProperty("class", "StepContainer")
        progress_layout = QVBoxLayout(progress_container)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        self.status_label = QLabel('Ready')
        self.detailed_status = QTextEdit()
        self.detailed_status.setReadOnly(True)
        self.detailed_status.setMaximumHeight(100)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.detailed_status)
        
        download_layout.addWidget(progress_container)
        download_layout.addStretch()
        
        self.stack.addWidget(download_page)

        # Window setup
        self.setMinimumSize(600, 700)
        self.resize(800, 800)
        self.center_window()

    def center_window(self):
        qr = self.frameGeometry()
        cp = QApplication.desktop().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def browse_location(self):
        default_dir = self.save_path.text() or os.path.expanduser("~/Downloads")
        folder = QFileDialog.getExistingDirectory(self, "Select Download Location", default_dir)
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
            self.video_info_label.setText(f"Found: {title}\n" +
                                        (f"Playlist with {count} videos" if self.is_playlist else "Single video"))
            
            if self.is_playlist:
                self.count_input.setMaximum(count)
                self.count_input.setValue(count)
                self.stack.setCurrentIndex(1)  # Show playlist options
            else:
                self.count_input.setValue(1)
                self.stack.setCurrentIndex(2)  # Skip to download options
        else:
            QMessageBox.warning(self, 'Error', f'Invalid URL: {title}')

    def start_download(self):
        if not self.check_ffmpeg_installed():
            QMessageBox.critical(self, 'Error', 'ffmpeg is not installed. Please install ffmpeg to proceed.')
            return

        url = self.url_input.text().strip()
        save_path = self.save_path.text().strip()
        num_videos = 1 if not self.is_playlist else self.count_input.value()
        
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
        
        self.worker = DownloadWorker(
            url, 
            save_path, 
            format_id, 
            num_videos,
            is_playlist=self.is_playlist  # Pass is_playlist flag
        )
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
        # Auto-scroll to bottom
        self.detailed_status.verticalScrollBar().setValue(
            self.detailed_status.verticalScrollBar().maximum()
        )

    def download_finished(self):
        self.download_btn.setEnabled(True)
        self.status_label.setText('Download completed successfully!')
        self.detailed_status.append('Download completed successfully!')
        self.show_completion_dialog(True)

    def download_error(self, error):
        """Handle download errors"""
        self.download_btn.setEnabled(True)
        self.status_label.setText('Error occurred during download')
        self.detailed_status.append(f'Error: {error}')
        QMessageBox.critical(self, 'Error', f'Download failed: {error}')
        
        # Optionally ask if user wants to try again
        reply = QMessageBox.question(
            self, 'Retry Download',
            'Would you like to try downloading again?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.reset_for_new_download()
        else:
            # Show download more/quit dialog
            self.show_completion_dialog(False)
    
    def show_completion_dialog(self, success=True):
        """Show completion dialog with download more/quit options"""
        dialog = QDialog(self)
        dialog.setWindowTitle('Download Status')
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 14px;
                margin: 10px;
            }
            QPushButton {
                margin: 10px;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        message = QLabel('Download completed successfully!' if success else 'Download failed.')
        message.setAlignment(Qt.AlignCenter)
        layout.addWidget(message)
        
        btn_layout = QHBoxLayout()
        
        download_more_btn = QPushButton('Download More')
        download_more_btn.clicked.connect(lambda: self.reset_for_new_download(dialog))
        
        quit_btn = QPushButton('Quit')
        quit_btn.setStyleSheet("background-color: #dc3545;")
        quit_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(download_more_btn)
        btn_layout.addWidget(quit_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec_()

    def reset_for_new_download(self, dialog=None):
        """Reset the UI for a new download"""
        if dialog:
            dialog.accept()
        
        # Clear inputs
        self.url_input.clear()
        self.save_path.setText(os.path.expanduser("~/Downloads"))
        self.progress_bar.setValue(0)
        self.status_label.setText('Ready')
        self.detailed_status.clear()
        
        # Reset to first step
        self.stack.setCurrentIndex(0)
        self.validate_btn.setEnabled(True)
        self.download_btn.setEnabled(True)

    # Add new method to handle window close
    def closeEvent(self, event):
        if self.download_btn.isEnabled():  # Only show confirmation if not downloading
            reply = QMessageBox.question(
                self, 'Exit',
                'Are you sure you want to quit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            reply = QMessageBox.warning(
                self, 'Download in Progress',
                'A download is in progress. Quitting now will cancel it.\nAre you sure?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                # Could add cleanup code here if needed
                event.accept()
            else:
                event.ignore()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Adjust layouts based on window size
        width = event.size().width()
        if width < 800:
            self.url_input.setMinimumWidth(300)
        else:
            self.url_input.setMinimumWidth(400)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())