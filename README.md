# 🎤 Karaoke Video Maker

Desktop application for creating karaoke videos from LRC lyric files and audio.

![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue)
![Python](https://img.shields.io/badge/python-3.9+-yellow)

---

## Features

- 🎵 **LRC parsing** — reads standard `.lrc` files with timestamps
- 🎬 **Video generation** — creates MP4 with word-by-word karaoke highlighting
- 🖼️ **Background image** — optional image as video background (letterboxed, no crop)
- 📐 **Text area control** — precise X/Y/W/H positioning of lyrics on screen
- 🎨 **Customizable appearance** — font size, bold, highlight/inactive colors, text background color
- 👁️ **Live preview** — real-time preview with time scrubber
- 📊 **Progress tracking** — progress bar and log during rendering

---

## Installation

### Prerequisites

- Python 3.9 or higher
- pip

### Install dependencies

```bash
pip install moviepy PyQt6 pillow numpy
```

For building standalone executable:

```bash
pip install pyinstaller
```

---

## Running the App

### Desktop application (GUI)

```bash
python karaoke_app.py
```

### Command-line video generation

```bash
python lrc_to_video.py
```

Edit the settings at the bottom of `lrc_to_video.py` to specify your files:

```python
LRC_FILE = 'song.lrc'
AUDIO_FILE = 'song.mp3'
OUTPUT_FILE = 'karaoke.mp4'
FONT_SIZE = 50
BG_IMAGE = 'background.jpg'  # or None
TEXT_RECT = (100, 400, 1080, 280)  # (x, y, width, height)
```

---

## Running on Apple Silicon (M1/M2/M3)

### Running from source (recommended)

```bash
pip install moviepy PyQt6 pillow numpy
python karaoke_app.py
```

### Running the standalone app

```bash
open dist/KaraokeVideoMaker.app
```

If macOS blocks the app (Gatekeeper warning):

```bash
# Remove quarantine attribute (if downloaded/transferred)
xattr -d com.apple.quarantine dist/KaraokeVideoMaker.app 2>/dev/null

# Or go to: System Settings → Privacy & Security → Security
# Click "Open Anyway" next to the blocked app warning
```

If you get a `Killed: 9` error:
1. Open **Terminal**
2. Navigate to the app contents:
   ```bash
   dist/KaraokeVideoMaker.app/Contents/MacOS/KaraokeVideoMaker
   ```
3. If it shows an error about code signing, re-sign it:
   ```bash
   codesign --force --deep --sign - dist/KaraokeVideoMaker.app
   ```

---

## Building Standalone Executable

### macOS

```bash
python build.py
# or with clean build:
python build.py --clean
```

Output: `dist/KaraokeVideoMaker.app`

### Windows

```bash
python build.py
# or with clean build:
python build.py --clean
```

Output: `dist\KaraokeVideoMaker\KaraokeVideoMaker.exe`

### Build improvements

The updated build script now includes:
- **Bundled fonts** — DejaVu Sans fonts are included in the executable package
- **Cross-platform font detection** — automatically uses system fonts if bundled fonts fail
- **All dependencies** — PyQt6, moviepy, PIL, numpy, imageio and all their submodules
- **Better error handling** — font loading errors are now reported gracefully

### Custom icon

Place `icon.jpeg` in the project root, then generate platform-specific icon files:

```bash
python generate_icons.py
```

This creates:
- `icon.icns` — macOS icon (10 sizes, 16×16 to 1024×1024 @2x)
- `icon.ico` — Windows icon (6 layers, 16×16 to 256×256)

Then rebuild:

```bash
python build.py --clean
```

---

## GUI Usage Guide

### Layout

The window is split into two panes:

#### Left Pane — Controls

**📂 Files**
| Field        | Description                                                  |
| ------------ | ------------------------------------------------------------ |
| **LRC**      | Path to `.lrc` lyrics file                                   |
| **Audio**    | Path to audio file (`.mp3`, `.wav`, `.ogg`, `.flac`, `.m4a`) |
| **BG image** | Optional background image (`.jpg`, `.png`)                   |
| **Output**   | Output video file path                                       |

**📐 Text Area** — position and size of lyrics on the 1280×720 canvas
| Control     | Description                                      |
| ----------- | ------------------------------------------------ |
| **X, Y**    | Top-left corner position                         |
| **W, H**    | Width and height of text area                    |
| **Presets** | Bottom / Center / Full / Top — quick positioning |

**🎨 Appearance**
| Control       | Description                                                    |
| ------------- | -------------------------------------------------------------- |
| **Font size** | Text size (16–120)                                             |
| **Bold**      | Toggle bold font (Helvetica Bold)                              |
| **Highlight** | Color of highlighted (active) words                            |
| **Inactive**  | Color of unhighlighted words                                   |
| **Text BG**   | Background color behind text (with alpha/transparency support) |

#### Right Pane — Preview & Render

**👁️ Preview** — 16:9 preview window showing exactly how the video will look
- **Time slider** — scrub through the song to preview different moments
- Preview updates automatically when you change any setting

**🎬 Generate Video** — start rendering
- Progress bar shows percentage of frames rendered
- Log shows detailed status and any errors

---

## LRC File Format

Standard LRC format with timestamps:

```
[ti:Song Title]
[ar:Artist Name]
[00:28.463]First line of lyrics
[00:31.317]Second line of lyrics
[00:34.848]Third line of lyrics
```

Supported metadata tags: `ti` (title), `ar` (artist), `al` (album), `by` (creator).

---

## Output

- **Resolution:** 1280×720 (HD)
- **FPS:** 24
- **Video codec:** H.264 (libx264)
- **Audio codec:** AAC
- **Background:** If image is provided, it is letterboxed (fit with black bars) — no cropping

---

## Project Structure

```
python-presentation/
├── karaoke_app.py          # PyQt6 desktop application
├── lrc_to_video.py         # CLI video generator
├── build.py                # PyInstaller build script
├── generate_icons.py       # Icon generator from JPEG
├── icon.jpeg               # Source icon image
├── icon.icns               # macOS icon (generated)
├── icon.ico                # Windows icon (generated)
├── fonts/                  # Bundled fonts (cross-platform)
│   ├── DejaVuSans.ttf      # Regular font
│   └── DejaVuSans-Bold.ttf # Bold font
├── song.lrc                # Example LRC file
├── song.mp3                # Example audio file
├── karaoke.mp4             # Generated video
├── background.jpg          # Optional background image
├── dist/                   # Built applications
│   └── KaraokeVideoMaker/
│       ├── KaraokeVideoMaker.exe
│       └── _internal/      # Dependencies (including fonts)
└── README.md               # This file
```

---

## Troubleshooting

### "Font not found" error
The app now includes **DejaVu Sans** font (bundled in the `fonts/` directory) which works on both macOS and Windows.
If the bundled fonts are not found, the app automatically falls back to system fonts:
- **Windows:** Arial → Segoe UI → Calibri
- **macOS:** Helvetica → Helvetica Neue → SF Pro
- **Linux:** DejaVu Sans (system)

### App crashes after selecting a file (Windows build)
This was caused by hardcoded macOS font paths (`/System/Library/Fonts/...`). 
**Fixed in this version:** The build now includes bundled fonts and automatically detects platform-specific fonts.

### Slow rendering
Rendering time depends on audio duration. A 4-minute song takes ~5-10 minutes to render. The preview renders instantly since it generates only one frame.

### Preview not updating
Make sure both LRC and audio files are selected. The preview requires parsed lyrics to display anything.

### Build fails on Windows
Install the Visual C++ Build Tools and ensure `ffmpeg` is available in your PATH. PyInstaller may require `--collect-all PyQt6` — the `build.py` script already includes this.
