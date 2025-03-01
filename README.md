# YouTube Downloader

A modern and user-friendly desktop application for downloading YouTube videos and playlists with an intuitive graphical interface.

![YouTube Downloader Interface](screenshot.png)

## Features

- 📥 Download single videos or entire playlists from YouTube
- 📝 Select specific video ranges in playlists
- 🎥 Multiple quality options (1080p, 720p, 480p, 360p)
- 🎵 Audio-only download option
- 📊 Real-time download progress with detailed statistics
- 💫 Modern and responsive user interface
- 📁 Custom save location selection
- 📋 Playlist video preview before downloading
- ⚡ Download speed and ETA display
- 📝 Detailed logging of download progress

## Requirements

- Python 3.7 or higher
- FFmpeg (required for video processing)
- PyQt5
- yt-dlp

## Installation

1. **Clone or download this repository**
```bash
git clone <repository-url>
cd "Playlist Downloader"
```

2. **Install Python dependencies**
```bash
pip install PyQt5 yt-dlp
```

3. **Install FFmpeg**

- **Windows:**
  - Download FFmpeg from [official website](https://ffmpeg.org/download.html)
  - Add FFmpeg to your system's PATH environment variable
  
- **macOS:**
  ```bash
  brew install ffmpeg
  ```
  
- **Linux:**
  ```bash
  sudo apt-get update
  sudo apt-get install ffmpeg
  ```

## Usage

1. **Start the application:**
```bash
python youtube_downloader.py
```

2. **Download a Video or Playlist:**
   - Paste the YouTube URL in the input field
   - Click "Validate URL" to verify and load video/playlist information
   - For playlists: Select the range of videos you want to download
   - Choose your preferred video quality
   - Select the save location
   - Click "Start Download"

3. **Monitor Download Progress:**
   - View real-time download speed
   - Check estimated time remaining
   - Monitor file size and progress
   - View detailed log information

## Quality Options

- Best Quality (Video + Audio)
- HD 1080p
- HD 720p
- SD 480p
- SD 360p
- Audio Only (MP3)

## Troubleshooting

1. **FFmpeg not found error:**
   - Make sure FFmpeg is properly installed
   - Verify FFmpeg is added to system PATH
   - Restart the application after installing FFmpeg

2. **Invalid URL error:**
   - Ensure the YouTube URL is correct and accessible
   - Check your internet connection

3. **Download fails:**
   - Check your internet connection
   - Verify you have sufficient disk space
   - Make sure the save location is accessible

## Known Limitations

- Some videos might not be available in all quality options
- Download speed depends on your internet connection
- YouTube's terms of service and restrictions apply

## Contributing

Feel free to fork this repository and submit pull requests for any improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [PyQt5](https://www.riverbankcomputing.com/software/pyqt/)
- Uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) for video downloading
- FFmpeg for video processing