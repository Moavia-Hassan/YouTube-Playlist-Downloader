import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import yt_dlp

class UrlValidator(QThread):
    finished = pyqtSignal(bool, str, int, list)  # Added list for video titles
    
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
                
                # Get video titles for playlist
                video_titles = []
                if is_playlist:
                    for entry in info['entries']:
                        video_titles.append(entry.get('title', 'Unknown Title'))
                
                self.finished.emit(True, title, video_count, video_titles)
        except Exception as e:
            self.finished.emit(False, str(e), 0, [])

class DownloadWorker(QThread):
    progress = pyqtSignal(float)
    status = pyqtSignal(str)
    finished = pyqtSignal()
    download_error = pyqtSignal(str)  # Renamed from error to download_error
    detailed_progress = pyqtSignal(dict)  # New signal for detailed progress

    def __init__(self, url, save_path, format_id, num_videos, start_index=1, end_index=None, is_playlist=False):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.format_id = format_id
        self.num_videos = num_videos
        self.is_playlist = is_playlist
        self.start_index = start_index
        self.end_index = end_index if end_index else num_videos
        self.current_video = 0  # Track current video number
        self.last_progress = 0
        self.smoothed_progress = 0
        self.progress_history = []
        self.current_video = 0
        self.total_progress = 0
        self.current_video_progress = 0
        self.overall_progress = 0

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            # Calculate speed and progress
            speed = d.get('speed', 0)
            speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else "N/A"

            # Get downloaded and total size
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)

            if total > 0:
                # Calculate individual video progress
                self.current_video_progress = (downloaded / total) * 100
                
                # Calculate overall progress for playlist
                if self.is_playlist:
                    video_weight = 100.0 / self.num_videos
                    base_progress = self.current_video * video_weight
                    current_part = (self.current_video_progress * video_weight) / 100
                    self.overall_progress = base_progress + current_part
                else:
                    self.overall_progress = self.current_video_progress

                # Smooth progress updates
                alpha = 0.1
                self.smoothed_progress = (alpha * self.overall_progress + 
                                        (1 - alpha) * self.last_progress)
                self.last_progress = self.smoothed_progress
                
                self.progress.emit(self.smoothed_progress)
                progress_str = f"{self.smoothed_progress:.1f}%"
            else:
                progress_str = "Calculating..."

            # Format file size and time
            total_size = f"{total/1024/1024:.1f} MB" if total else "Unknown"
            downloaded_size = f"{downloaded/1024/1024:.1f}"
            
            # Calculate ETA
            eta = d.get('eta', None)
            if eta is not None:
                m, s = divmod(eta, 60)
                h, m = divmod(m, 60)
                eta_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
            else:
                eta_str = "Calculating..."

            # Get clean filename without path
            filename = os.path.basename(d.get('filename', ''))
            
            # Update progress info
            progress_info = {
                'speed': speed_str,
                'downloaded': downloaded_size,
                'total': total_size,
                'video_num': self.current_video + 1,
                'filename': filename,
                'percent': progress_str,
                'eta': eta_str,
                'total_videos': self.num_videos
            }
            
            self.detailed_progress.emit(progress_info)
            
        elif d['status'] == 'finished':
            self.current_video += 1
            self.current_video_progress = 0
            self.status.emit('Processing completed file...')

    def run(self):
        try:
            ydl_opts = {
                'format': self.format_id,
                'outtmpl': os.path.join(self.save_path, f'%(playlist_index)03d_%(title)s.%(ext)s' if self.is_playlist else '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'noplaylist': not self.is_playlist,
                'playlist_items': f'{self.start_index}-{self.end_index}' if self.is_playlist else None,
                'logger': self,  # Add this line
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.status.emit('Starting download...')
                ydl.download([self.url])
            
            self.finished.emit()
        except Exception as e:
            self.download_error.emit(str(e))

    # Add these methods for logging
    def debug(self, msg):
        if msg.strip():
            self.status.emit(msg)

    def warning(self, msg):
        if msg.strip():
            self.status.emit(f"Warning: {msg}")

    def error(self, msg):
        if msg.strip():
            self.status.emit(f"Error: {msg}")
            self.download_error.emit(msg)  # Use download_error signal instead

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.current_step = 0
        self.video_count = 0
        self.is_playlist = False
        self.selected_count = 1  # Add this line to store selected count

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
        
        # Options container (store reference)
        self.options_container = QFrame()
        self.options_container.setProperty("class", "StepContainer")
        options_layout = QVBoxLayout(self.options_container)
        
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
        
        download_layout.addWidget(self.options_container)
        
        # Progress view with modern styling
        self.progress_view = QFrame()
        self.progress_view.setObjectName("downloadProgress")
        self.progress_view.hide()
        progress_layout = QVBoxLayout(self.progress_view)
        progress_layout.setSpacing(15)
        
        # Download status header
        status_container = QFrame()
        status_container.setObjectName("statusContainer")
        status_layout = QHBoxLayout(status_container)
        self.status_label = QLabel("Ready to download")
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)
        progress_layout.addWidget(status_container)
        
        # File info and progress section
        progress_container = QFrame()
        progress_container.setObjectName("progressContainer")
        progress_inner = QVBoxLayout(progress_container)
        progress_inner.setSpacing(10)
        
        # Current file label
        self.current_file_label = QLabel()
        self.current_file_label.setObjectName("fileLabel")
        self.current_file_label.setWordWrap(True)
        progress_inner.addWidget(self.current_file_label)
        
        # Progress bar with percentage
        progress_bar_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_percent = QLabel("0%")
        self.progress_percent.setObjectName("percentLabel")
        progress_bar_layout.addWidget(self.progress_bar, stretch=1)
        progress_bar_layout.addWidget(self.progress_percent)
        progress_inner.addLayout(progress_bar_layout)
        
        # Download statistics grid
        stats_layout = QGridLayout()
        stats_layout.setSpacing(10)
        
        # Add labels with modern styling
        self.speed_label = QLabel("Speed: --")
        self.time_label = QLabel("Time left: --:--")
        self.size_label = QLabel("Size: --")
        self.video_progress_label = QLabel("Progress: --")
        
        for label in [self.speed_label, self.time_label, self.size_label, self.video_progress_label]:
            label.setObjectName("statsLabel")
        
        stats_layout.addWidget(self.speed_label, 0, 0)
        stats_layout.addWidget(self.time_label, 0, 1)
        stats_layout.addWidget(self.size_label, 1, 0)
        stats_layout.addWidget(self.video_progress_label, 1, 1)
        
        progress_inner.addLayout(stats_layout)
        progress_layout.addWidget(progress_container)
        
        # Log view with styled scrollbar
        self.detailed_status = QTextEdit()
        self.detailed_status.setObjectName("logView")
        self.detailed_status.setReadOnly(True)
        self.detailed_status.setMinimumHeight(200)
        self.detailed_status.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                border: none;
                border-radius: 4px;
                color: #00ff00;
                font-family: 'Consolas', monospace;
                padding: 10px;
            }
            QScrollBar:vertical {
                background-color: #1a1a1a;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #404040;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #505050;
            }
        """)
        progress_layout.addWidget(self.detailed_status)
        
        download_layout.addWidget(self.progress_view)
        
        # Add modern progress view styles
        self.setStyleSheet(self.styleSheet() + """
            QFrame#downloadProgress {
                background-color: #1a1a1a;
                border-radius: 10px;
                padding: 20px;
            }
            QFrame#statusContainer {
                background-color: #232323;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel#statusLabel {
                color: #4dabf7;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel#fileLabel {
                color: #e9ecef;
                font-size: 14px;
                margin-bottom: 5px;
            }
            QLabel#percentLabel {
                color: #4dabf7;
                font-size: 16px;
                font-weight: bold;
                min-width: 60px;
            }
            QLabel#statsLabel {
                color: #adb5bd;
                font-size: 13px;
            }
            QProgressBar {
                background-color: #232323;
                border: none;
                border-radius: 3px;
                height: 6px;
                text-align: center;
                margin-top: 2px;
                margin-bottom: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4dabf7,
                    stop:1 #228be6);
                border-radius: 3px;
            }
            QTextEdit#logView {
                background-color: #232323;
                border: none;
                border-radius: 8px;
                color: #adb5bd;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 10px;
                margin-top: 10px;
            }
        """)

        download_layout.addWidget(self.progress_view)
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

    def handle_validation_result(self, is_valid, title, count, video_titles):
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText('Validate URL')
        
        if is_valid:
            self.video_count = count
            self.is_playlist = count > 1
            self.video_titles = video_titles
            self.video_info_label.setText(f"Found: {title}\n" +
                                        (f"Playlist with {count} videos" if self.is_playlist else "Single video"))
            
            if self.is_playlist:
                self.setup_playlist_options(count, video_titles)
                self.stack.setCurrentIndex(1)  # Show playlist options
            else:
                self.count_input.setValue(1)
                self.stack.setCurrentIndex(2)  # Skip to download options
        else:
            QMessageBox.warning(self, 'Error', f'Invalid URL: {title}')

    def setup_playlist_options(self, count, video_titles):
        # Clear existing widgets in playlist container
        for i in reversed(range(self.stack.widget(1).layout().count())):
            item = self.stack.widget(1).layout().itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        playlist_layout = QVBoxLayout()
        
        # Info container
        info_container = QFrame()
        info_container.setProperty("class", "StepContainer")
        info_layout = QVBoxLayout(info_container)
        info_layout.addWidget(self.video_info_label)
        playlist_layout.addWidget(info_container)
        
        # Range selection
        range_container = QFrame()
        range_container.setProperty("class", "StepContainer")
        range_layout = QVBoxLayout(range_container)
        
        range_label = QLabel("Select Video Range:")
        range_label.setProperty("class", "StepTitle")
        
        range_inputs = QHBoxLayout()
        self.start_index = QSpinBox()
        self.start_index.setMinimum(1)
        self.start_index.setMaximum(count)
        self.end_index = QSpinBox()
        self.end_index.setMinimum(1)
        self.end_index.setMaximum(count)
        self.end_index.setValue(count)
        
        # Connect value changed signals
        self.start_index.valueChanged.connect(self.update_selected_count)
        self.end_index.valueChanged.connect(self.update_selected_count)
        
        range_inputs.addWidget(QLabel("From:"))
        range_inputs.addWidget(self.start_index)
        range_inputs.addWidget(QLabel("To:"))
        range_inputs.addWidget(self.end_index)
        
        range_layout.addWidget(range_label)
        range_layout.addLayout(range_inputs)
        playlist_layout.addWidget(range_container)
        
        # Video list
        video_list = QTextEdit()
        video_list.setReadOnly(True)
        for i, title in enumerate(video_titles, 1):
            video_list.append(f"{i:03d}. {title}")
        
        list_container = QFrame()
        list_container.setProperty("class", "StepContainer")
        list_layout = QVBoxLayout(list_container)
        list_layout.addWidget(QLabel("Videos in playlist:"))
        list_layout.addWidget(video_list)
        playlist_layout.addWidget(list_container)
        
        # Next button
        next_btn = QPushButton('Next')
        next_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        playlist_layout.addWidget(next_btn)
        
        # Set the new layout
        playlist_widget = self.stack.widget(1)
        QWidget().setLayout(playlist_widget.layout())  # Clear old layout
        playlist_widget.setLayout(playlist_layout)
        
        # Initialize selected count
        self.update_selected_count()

    def update_selected_count(self):
        """Update the selected video count based on range selection"""
        if hasattr(self, 'start_index') and hasattr(self, 'end_index'):
            start = self.start_index.value()
            end = self.end_index.value()
            self.selected_count = end - start + 1
    
    def start_download(self):
        if not self.check_ffmpeg_installed():
            QMessageBox.critical(self, 'Error', 'ffmpeg is not installed. Please install ffmpeg to proceed.')
            return

        url = self.url_input.text().strip()
        save_path = self.save_path.text().strip()
        
        if not url or not save_path:
            QMessageBox.warning(self, 'Error', 'Please enter URL and select save location')
            return

        # Store selected count before clearing UI
        num_videos = self.selected_count if self.is_playlist else 1
        start_idx = self.start_index.value() if hasattr(self, 'start_index') else 1
        end_idx = self.end_index.value() if hasattr(self, 'end_index') else 1
        
        # Clear and update UI
        self.clear_ui_for_download()
        
        # Show progress view and hide options
        self.progress_view.show()
        self.options_container.hide()
        
        format_id = self.get_format_id()
        
        try:
            self.worker = DownloadWorker(
                url, 
                save_path, 
                format_id, 
                num_videos,
                start_index=start_idx,
                end_index=end_idx,
                is_playlist=self.is_playlist
            )
            self.worker.progress.connect(self.update_progress)
            self.worker.status.connect(self.update_status)
            self.worker.detailed_progress.connect(self.update_detailed_progress)
            self.worker.finished.connect(self.download_finished)
            self.worker.download_error.connect(self.download_error)
            self.worker.start()
        except Exception as e:
            self.download_error(str(e))

    def clear_ui_for_download(self):
        """Clear UI and prepare for download"""
        # Clear progress information
        self.progress_bar.setValue(0)
        self.status_label.setText('Initializing download...')
        self.detailed_status.clear()
        self.speed_label.setText('Speed: N/A')
        self.size_label.setText('Size: N/A')
        self.video_progress_label.setText('Progress: N/A')
        self.current_file_label.setText('Current File: N/A')
        
        # Disable inputs
        self.url_input.setEnabled(False)
        self.validate_btn.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.save_path.setEnabled(False)
        self.download_btn.setEnabled(False)

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

    def update_detailed_progress(self, progress_info):
        """Update progress information with improved formatting"""
        # Update filename - show only the title
        self.current_file_label.setText(progress_info['filename'])
        
        # Update progress percentage
        self.progress_percent.setText(progress_info['percent'])
        
        # Update download speed with icon
        self.speed_label.setText(f"⚡ {progress_info['speed']}")
        
        # Update file size
        self.size_label.setText(f"📦 {progress_info['downloaded']} / {progress_info['total']}")
        
        # Update time remaining
        self.time_label.setText(f"⏱️ {progress_info['eta']}")
        
        # Update video progress for playlists
        if self.is_playlist:
            current = progress_info['video_num']
            total = progress_info['total_videos']
            self.video_progress_label.setText(f"Video {current} of {total}")
        
        # Update status text
        status = (f"Downloading video {progress_info['video_num']} "
                f"• {progress_info['speed']} "
                f"• {progress_info['percent']}")
        self.status_label.setText(status)
        
        # Add to log with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.detailed_status.append(
            f"[{timestamp}] {progress_info['filename']} - "
            f"{progress_info['percent']} at {progress_info['speed']}"
        )

    def download_finished(self):
        """Handle download completion"""
        # Re-enable inputs and restore view
        self.url_input.setEnabled(True)
        self.validate_btn.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.save_path.setEnabled(True)
        self.download_btn.setEnabled(True)
        
        # Show options and hide progress
        self.options_container.show()
        self.progress_view.hide()
        
        self.status_label.setText('Download completed successfully!')
        self.detailed_status.append('Download completed successfully!')
        self.show_completion_dialog(True)

    def download_error(self, error):
        """Handle download errors"""
        # Re-enable inputs and restore view
        self.url_input.setEnabled(True)
        self.validate_btn.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.save_path.setEnabled(True)
        self.download_btn.setEnabled(True)
        
        # Show options and hide progress
        self.options_container.show()
        self.progress_view.hide()
        
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
        
        # Clear all progress information
        self.speed_label.setText('Speed: N/A')
        self.size_label.setText('Size: N/A')
        self.video_progress_label.setText('Progress: N/A')
        self.current_file_label.setText('Current File: N/A')
        
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