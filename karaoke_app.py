import sys
import os
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoClip, AudioFileClip
from proglog import ProgressBarLogger

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton,
    QSpinBox, QSlider, QColorDialog, QFileDialog, QProgressBar,
    QTextEdit, QMessageBox, QFrame, QCheckBox, QListWidget, QListWidgetItem,
    QSplitter,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QColor, QPalette, QFont, QPainter, QPen, QBrush, QPixmap, QImage
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

FPS = 24

# ─── Font resolution (bundled → system fallbacks) ────────────

def _get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller bundle."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller temp folder
        return os.path.join(sys._MEIPASS, relative_path)
    # Development: relative to script location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)


def _find_system_font():
    """Find a suitable system font based on platform."""
    system = sys.platform
    if system == 'darwin':
        candidates = [
            '/System/Library/Fonts/Helvetica.ttc',
            '/System/Library/Fonts/HelveticaNeue.ttc',
            '/System/Library/Fonts/SFNSDisplay.ttf',
        ]
    elif system == 'win32':
        windir = os.environ.get('WINDIR', r'C:\Windows')
        candidates = [
            os.path.join(windir, 'Fonts', 'arial.ttf'),
            os.path.join(windir, 'Fonts', 'segoeui.ttf'),
            os.path.join(windir, 'Fonts', 'calibri.ttf'),
        ]
    else:
        candidates = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/TTF/DejaVuSans.ttf',
        ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def get_font_paths():
    """Return (regular_font_path, bold_font_path, bold_index_or_none)."""
    # First try bundled fonts
    bundled_regular = _get_resource_path('fonts/DejaVuSans.ttf')
    bundled_bold = _get_resource_path('fonts/DejaVuSans-Bold.ttf')
    if os.path.exists(bundled_regular) and os.path.exists(bundled_bold):
        return bundled_regular, bundled_bold, None

    # Fallback to system fonts
    system_font = _find_system_font()
    if system_font:
        # For macOS Helvetica (index 1 = bold)
        if sys.platform == 'darwin' and 'Helvetica' in system_font:
            return system_font, system_font, 1
        # Windows/Linux: try same file or search for bold variant
        parent = os.path.dirname(system_font)
        base = os.path.basename(system_font)
        name_no_ext = os.path.splitext(base)[0]
        ext = os.path.splitext(base)[1]
        # Try common bold naming conventions
        for suffix in ['-Bold', ' Bold', 'B', '']:
            candidate = os.path.join(parent, f"{name_no_ext}{suffix}{ext}")
            if os.path.exists(candidate):
                return system_font, candidate, None
        return system_font, system_font, None

    # Last resort: bundled path even if missing (will error gracefully)
    return bundled_regular, bundled_bold, None


FONT_PATH, FONT_PATH_BOLD, FONT_INDEX_BOLD = get_font_paths()
VIDEO_W, VIDEO_H = 1280, 720


# ─── LRC parsing ───────────────────────────────────────────────

def parse_lrc(lrc_file):
    with open(lrc_file, 'r', encoding='utf-8') as f:
        content = f.read()

    metadata = {}
    patterns = {'ti': r'\[ti:(.*?)\]', 'ar': r'\[ar:(.*?)\]'}
    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            metadata[key] = match.group(1).strip()

    lines = []
    # Support both single [time]text and dual [start][end]text formats
    for match in re.finditer(r'\[(\d+):(\d+\.\d+)\](?:\[(\d+):(\d+\.\d+)\])?(.*)', content):
        start_min, start_sec = int(match.group(1)), float(match.group(2))
        start_time_sec = start_min * 60 + start_sec
        
        end_min, end_sec = match.group(3), match.group(4)
        if end_min is not None and end_sec is not None:
            end_time_sec = int(end_min) * 60 + float(end_sec)
        else:
            end_time_sec = None
        
        text = match.group(5).strip()
        if text:
            lines.append({
                'time': start_time_sec,
                'end': end_time_sec,
                'text': text
            })

    lines.sort(key=lambda x: x['time'])
    return metadata, lines


def split_words_with_timing(lines, audio_duration, fontsize, font_regular, font_bold=None):
    """Build enriched lines with pre-computed word widths for both regular and bold."""
    word_timeline = []
    enriched_lines = []

    for i, line in enumerate(lines):
        # Use explicit end time if available, otherwise fallback to next line start
        if line.get('end') is not None:
            line_duration = max(line['end'] - line['time'], 0.1)
        else:
            next_time = lines[i + 1]['time'] if i + 1 < len(lines) else audio_duration
            line_duration = max(next_time - line['time'], 1.0)
        words = line['text'].split()
        if not words:
            enriched_lines.append({
                'time': line['time'], 'text': line['text'],
                'word_starts': [], 'word_durations': [],
                'word_widths': [], 'word_widths_bold': [],
                'total_width': 0, 'total_width_bold': 0,
            })
            continue

        word_dur = line_duration / len(words)
        word_starts = []
        word_durations = []
        word_widths = []
        word_widths_bold = []
        total_width = 0
        total_width_bold = 0
        for j, word in enumerate(words):
            w_start = line['time'] + j * word_dur
            w_dur = word_dur
            word_starts.append(w_start)
            word_durations.append(w_dur)

            bbox = font_regular.getbbox(word)
            ww = bbox[2] - bbox[0]
            word_widths.append(ww)
            gap = 10 if j < len(words) - 1 else 0
            total_width += ww + gap

            if font_bold:
                bbox_b = font_bold.getbbox(word)
                ww_b = bbox_b[2] - bbox_b[0]
            else:
                ww_b = ww
            word_widths_bold.append(ww_b)
            total_width_bold += ww_b + gap

            word_timeline.append({
                'text': word,
                'start': w_start,
                'line_time': line['time'],
            })
        enriched_lines.append({
            'time': line['time'],
            'end': line.get('end'),
            'text': line['text'],
            'word_starts': word_starts,
            'word_durations': word_durations,
            'word_widths': word_widths,
            'word_widths_bold': word_widths_bold,
            'total_width': total_width,
            'total_width_bold': total_width_bold,
            'words': words,
        })

    return word_timeline, enriched_lines


# ─── Frame rendering ───────────────────────────────────────────

def render_frame(t, width, height, enriched_lines, fontsize, font,
                 text_rect, highlight_color, unhighlighted_color,
                 bg_prepared=None, text_bg_color=(0, 0, 0, 140), bold=False):
    if bg_prepared is not None:
        img = bg_prepared.copy()
    else:
        img = Image.new('RGB', (width, height), (20, 20, 30))

    draw = ImageDraw.Draw(img)
    rx, ry, rw, rh = text_rect
    lines_per_screen = 4
    ww_key = 'word_widths_bold' if bold else 'word_widths'
    tw_key = 'total_width_bold' if bold else 'total_width'

    for group_start in range(0, len(enriched_lines), lines_per_screen):
        group = enriched_lines[group_start:group_start + lines_per_screen]
        first_time = group[0]['time'] if group else 0
        next_first = enriched_lines[group_start + lines_per_screen]['time'] if group_start + lines_per_screen < len(enriched_lines) else first_time + 10

        if t < first_time or t >= next_first:
            continue

        total_height = len(group) * (fontsize + 20)
        start_y = ry + (rh - total_height) // 2

        for line_idx, line in enumerate(group):
            y = start_y + line_idx * (fontsize + 20)
            words = line.get('words', [])
            word_starts = line.get('word_starts', [])
            word_durations = line.get('word_durations', [])
            word_widths = line.get(ww_key, [])
            total_width = line.get(tw_key, 0)
            if not words:
                continue

            x = rx + (rw - total_width) // 2

            draw.rounded_rectangle(
                [x - 10, y - 4, x + total_width + 10, y + fontsize + 4],
                radius=8, fill=text_bg_color,
            )

            for word_idx, word in enumerate(words):
                ww = word_widths[word_idx]

                # Check if we're past the line's end time — keep highlighted
                line_end = line.get('end')

                # Calculate fill ratio (0.0 to 1.0)
                fill_ratio = 0.0
                if word_idx < len(word_starts):
                    elapsed = t - word_starts[word_idx]
                    if word_idx < len(word_durations) and word_durations[word_idx] > 0:
                        fill_ratio = min(max(elapsed / word_durations[word_idx], 0.0), 1.0)
                    elif elapsed > 0:
                        fill_ratio = 1.0

                # After line end, keep words highlighted
                if line_end is not None and t >= line_end:
                    fill_ratio = 1.0

                if fill_ratio <= 0:
                    # Fully unhighlighted
                    draw.text((x, y), word, fill=unhighlighted_color, font=font)
                elif fill_ratio >= 1:
                    # Fully highlighted
                    draw.text((x, y), word, fill=highlight_color, font=font)
                else:
                    # Partial fill: draw base, then overlay highlight clipped
                    draw.text((x, y), word, fill=unhighlighted_color, font=font)

                    # Create highlight layer clipped to fill portion
                    highlight_img = Image.new('RGBA', (ww, fontsize + 10), (0, 0, 0, 0))
                    hl_draw = ImageDraw.Draw(highlight_img)
                    hl_draw.text((0, 0), word, fill=highlight_color, font=font)

                    # Crop to fill width
                    fill_w = int(ww * fill_ratio)
                    if fill_w > 0:
                        highlight_img = highlight_img.crop((0, 0, fill_w, highlight_img.height))
                        img.paste(highlight_img, (x, y), highlight_img)

                x += ww + 10

    return np.array(img)


def prepare_background(bg_pil, width, height):
    """Resize background once, letterboxing to fit."""
    bw, bh = bg_pil.size
    scale = min(width / bw, height / bh)
    new_w = int(bw * scale)
    new_h = int(bh * scale)
    resized = bg_pil.resize((new_w, new_h), Image.LANCZOS)
    img = Image.new('RGB', (width, height), (0, 0, 0))
    img.paste(resized, ((width - new_w) // 2, (height - new_h) // 2))
    return img


# ─── Worker thread ─────────────────────────────────────────────

class RenderWorker(QThread):
    sig_log = pyqtSignal(str)
    sig_progress = pyqtSignal(int)
    sig_done = pyqtSignal(bool, str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            # Fix for macOS app bundle: MoviePy writes temp files to cwd by default,
            # which is read-only inside .app bundles. Force a writable temp dir.
            import tempfile
            os.environ['TMPDIR'] = tempfile.gettempdir()

            c = self.config
            self.sig_log.emit(f"📝 Parsing LRC: {c['lrc_file']}")
            metadata, lines = parse_lrc(c['lrc_file'])
            self.sig_log.emit(f"📊 {len(lines)} lines found")

            self.sig_log.emit(f"🎬 Loading audio: {c['audio_file']}")
            audio = AudioFileClip(c['audio_file'])
            duration = audio.duration
            self.sig_log.emit(f"⏱️ Duration: {duration:.2f}s")

            # Load fonts with error handling
            try:
                font_regular = ImageFont.truetype(FONT_PATH, c['fontsize'])
            except Exception as e:
                self.sig_log.emit(f"❌ Failed to load regular font: {FONT_PATH}")
                self.sig_log.emit(f"Error: {e}")
                self.sig_done.emit(False, f"Cannot load font: {FONT_PATH}")
                return

            try:
                font_bold_obj = ImageFont.truetype(
                    FONT_PATH_BOLD, c['fontsize'],
                    index=FONT_INDEX_BOLD if FONT_INDEX_BOLD is not None else 0,
                )
            except Exception as e:
                self.sig_log.emit(f"⚠️ Failed to load bold font, using regular: {e}")
                font_bold_obj = font_regular

            # Pre-prepare background
            bg_prepared = None
            if c.get('bg_image'):
                self.sig_log.emit(f"🖼️ Loading background: {c['bg_image']}")
                bg_pil = Image.open(c['bg_image']).convert('RGB')
                bg_prepared = prepare_background(bg_pil, VIDEO_W, VIDEO_H)
                bg_pil.close()

            # Build enriched lines with pre-computed widths
            self.sig_log.emit("⏱️ Calculating word timing...")
            _, enriched_lines = split_words_with_timing(
                lines, duration, c['fontsize'], font_regular, font_bold_obj,
            )

            # Choose which font to use for rendering
            font = font_bold_obj if c.get('bold') else font_regular

            text_rect = (c['tx'], c['ty'], c['tw'], c['th'])
            h_color = c['highlight_color']
            u_color = c['unhighlighted_color']
            text_bg = c.get('text_bg_color', (0, 0, 0, 140))

            def make_frame(t):
                return render_frame(
                    t, VIDEO_W, VIDEO_H, enriched_lines,
                    c['fontsize'], font, text_rect,
                    h_color, u_color, bg_prepared,
                    text_bg_color=text_bg, bold=c.get('bold', False),
                )

            self.sig_log.emit(f"📹 Creating video ({duration:.0f}s at {FPS}fps)...")
            video = VideoClip(make_frame, duration=duration)
            video = video.with_audio(audio)

            self.sig_log.emit(f"💾 Rendering to {c['output_file']}...")

            # Progress logger
            class MyLogger(ProgressBarLogger):
                def __init__(inner_self, log_fn, progress_fn):
                    super().__init__()
                    inner_self._log = log_fn
                    inner_self._progress = progress_fn
                    inner_self._total = None

                def bars_callback(inner_self, bar, attr, value, old_value=None):
                    if bar == 'frame_index' and attr == 'total' and old_value is None:
                        inner_self._total = value
                        inner_self._progress(0)
                    elif bar == 'frame_index' and attr == 'index' and inner_self._total is not None:
                        pct = int((value / inner_self._total) * 100)
                        inner_self._progress(pct)

            logger = MyLogger(self.sig_log.emit, self.sig_progress.emit)
            self.sig_log.emit("⏳ This may take a few minutes...")

            # Use absolute path for temp audio file to avoid read-only cwd issue
            import tempfile
            temp_audio_path = os.path.join(tempfile.gettempdir(), 'karaokeTEMP_MPY_wvf_snd.mp4')

            video.write_videofile(
                c['output_file'],
                fps=FPS,
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                bitrate='5000k',
                audio_bitrate='192k',
                logger=logger,
                temp_audiofile=temp_audio_path,
            )

            video.close()
            audio.close()

            self.sig_log.emit(f"✅ Done! → {c['output_file']}")
            self.sig_done.emit(True, c['output_file'])

        except Exception as e:
            self.sig_log.emit(f"❌ Error: {e}")
            import traceback
            self.sig_log.emit(traceback.format_exc())
            self.sig_done.emit(False, str(e))


# ─── Preview widget ────────────────────────────────────────────

class TextPreview(QFrame):
    """Shows a scaled preview of the text area rendered on the background image."""

    ASPECT = VIDEO_W / VIDEO_H  # 16:9

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: #1a1a2e; border-radius: 6px;")
        self.text_rect = (100, 400, 800, 280)
        self.enriched_lines = []
        self.highlight_color = '#FFD700'
        self.unhighlighted_color = '#AAAAAA'
        self.sample_t = 5.0
        self.bg_pil = None
        self.fontsize = 50
        self.font_obj = None
        self.bold = False
        self.text_bg_color = (0, 0, 0, 140)
        self.preview_pixmap = None
        self._img_data_ref = None

    def _render_preview(self):
        """Render preview frame using PIL, same as video rendering."""
        if not self.enriched_lines:
            self.preview_pixmap = None
            self.update()
            return

        font = self.font_obj if self.font_obj else ImageFont.truetype(FONT_PATH, self.fontsize)

        # Prepare background once
        bg_prepared = None
        if self.bg_pil is not None:
            bg_prepared = prepare_background(self.bg_pil, VIDEO_W, VIDEO_H)

        # Render at full video resolution
        frame_array = render_frame(
            self.sample_t, VIDEO_W, VIDEO_H,
            self.enriched_lines,
            self.fontsize, font, self.text_rect,
            self.highlight_color, self.unhighlighted_color,
            bg_prepared=bg_prepared,
            text_bg_color=self.text_bg_color,
            bold=self.bold,
        )

        # Scale down to widget size
        w, h = self.width(), self.height()
        pil_img = Image.fromarray(frame_array).resize((w, h), Image.LANCZOS)

        # Convert to QPixmap via QImage — keep reference to avoid GC
        img_data = pil_img.tobytes('raw', 'RGB')
        self._img_data_ref = img_data
        bytes_per_line = w * 3
        qimage = QImage(img_data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.preview_pixmap = QPixmap.fromImage(qimage)
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Adjust height to maintain 16:9 aspect ratio based on width
        new_height = int(self.width() / self.ASPECT)
        if new_height != self.height():
            self.setFixedHeight(new_height)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.preview_pixmap:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            # Draw pixmap filling widget (widget already 16:9)
            painter.drawPixmap(0, 0, self.width(), self.height(), self.preview_pixmap)

    def update_preview(self, text_rect, enriched_lines, h_color, u_color,
                       sample_t=0, bg_pil=None, fontsize=50,
                       bold=False, font=None, text_bg_color=None):
        self.text_rect = text_rect
        self.enriched_lines = enriched_lines
        self.highlight_color = h_color
        self.unhighlighted_color = u_color
        self.sample_t = sample_t
        self.bg_pil = bg_pil
        self.fontsize = fontsize
        self.font_obj = font
        self.bold = bold
        if text_bg_color is not None:
            self.text_bg_color = text_bg_color
        self._render_preview()


# ─── Main window ──────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('🎤 Karaoke Video Maker')
        self.setMinimumSize(1100, 700)

        # State
        self.lrc_file = ''
        self.audio_file = ''
        self.bg_image = ''
        self.parsed_lines = []

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(12)

        # ═══ LEFT PANE — Controls ═══
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        left.setMinimumWidth(380)
        left.setMaximumWidth(420)

        # ── Files ──
        file_group = QGroupBox('📂 Files')
        file_layout = QGridLayout(file_group)
        file_layout.setVerticalSpacing(4)
        file_layout.setHorizontalSpacing(4)

        file_layout.addWidget(QLabel('LRC:'), 0, 0)
        self.lrc_edit = QLineEdit()
        self.lrc_edit.setPlaceholderText('.lrc file…')
        self.lrc_edit.textChanged.connect(self._on_lrc_path_changed)
        file_layout.addWidget(self.lrc_edit, 0, 1)
        self.lrc_btn = QPushButton('…')
        self.lrc_btn.setFixedWidth(32)
        self.lrc_btn.clicked.connect(lambda: self._pick_file('lrc', self.lrc_edit))
        file_layout.addWidget(self.lrc_btn, 0, 2)

        file_layout.addWidget(QLabel('Audio:'), 1, 0)
        self.audio_edit = QLineEdit()
        self.audio_edit.setPlaceholderText('.mp3 / .wav / .ogg…')
        self.audio_edit.textChanged.connect(self._on_audio_path_changed)
        file_layout.addWidget(self.audio_edit, 1, 1)
        self.audio_btn = QPushButton('…')
        self.audio_btn.setFixedWidth(32)
        self.audio_btn.clicked.connect(lambda: self._pick_file('audio', self.audio_edit))
        file_layout.addWidget(self.audio_btn, 1, 2)

        file_layout.addWidget(QLabel('BG image:'), 2, 0)
        self.bg_edit = QLineEdit()
        self.bg_edit.setPlaceholderText('optional .jpg / .png…')
        self.bg_edit.textChanged.connect(self._update_preview_from_controls)
        file_layout.addWidget(self.bg_edit, 2, 1)
        self.bg_btn = QPushButton('…')
        self.bg_btn.setFixedWidth(32)
        self.bg_btn.clicked.connect(lambda: self._pick_file('image', self.bg_edit))
        file_layout.addWidget(self.bg_btn, 2, 2)

        file_layout.addWidget(QLabel('Output:'), 3, 0)
        self.out_edit = QLineEdit('karaoke.mp4')
        file_layout.addWidget(self.out_edit, 3, 1)
        self.out_btn = QPushButton('…')
        self.out_btn.setFixedWidth(32)
        self.out_btn.clicked.connect(self._pick_output)
        file_layout.addWidget(self.out_btn, 3, 2)

        left_layout.addWidget(file_group)

        # ── LRC Creator button ──
        self.lrc_creator_btn = QPushButton('🎵 Create LRC File (from audio + lyrics)')
        self.lrc_creator_btn.setFixedHeight(36)
        self.lrc_creator_btn.setStyleSheet('font-size: 13px; font-weight: bold;')
        self.lrc_creator_btn.clicked.connect(self._open_lrc_creator)
        left_layout.addWidget(self.lrc_creator_btn)

        # ── Text Area ──
        area_group = QGroupBox('📐 Text Area  (1280×720)')
        area_layout = QGridLayout(area_group)
        area_layout.setVerticalSpacing(4)
        area_layout.setHorizontalSpacing(4)

        area_layout.addWidget(QLabel('X:'), 0, 0)
        self.tx_spin = QSpinBox()
        self.tx_spin.setRange(0, VIDEO_W)
        self.tx_spin.setValue(100)
        self.tx_spin.valueChanged.connect(self._update_preview_from_controls)
        area_layout.addWidget(self.tx_spin, 0, 1)

        area_layout.addWidget(QLabel('Y:'), 1, 0)
        self.ty_spin = QSpinBox()
        self.ty_spin.setRange(0, VIDEO_H)
        self.ty_spin.setValue(400)
        self.ty_spin.valueChanged.connect(self._update_preview_from_controls)
        area_layout.addWidget(self.ty_spin, 1, 1)

        area_layout.addWidget(QLabel('W:'), 2, 0)
        self.tw_spin = QSpinBox()
        self.tw_spin.setRange(50, VIDEO_W)
        self.tw_spin.setValue(1080)
        self.tw_spin.valueChanged.connect(self._update_preview_from_controls)
        area_layout.addWidget(self.tw_spin, 2, 1)

        area_layout.addWidget(QLabel('H:'), 3, 0)
        self.th_spin = QSpinBox()
        self.th_spin.setRange(30, VIDEO_H)
        self.th_spin.setValue(280)
        self.th_spin.valueChanged.connect(self._update_preview_from_controls)
        area_layout.addWidget(self.th_spin, 3, 1)

        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(4)
        for label, vals in [
            ('Bottom', (100, 400, 1080, 280)),
            ('Center', (100, 200, 1080, 300)),
            ('Full', (40, 40, 1200, 640)),
            ('Top', (100, 40, 1080, 200)),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, v=vals: self._apply_preset(v))
            preset_layout.addWidget(btn)
        area_layout.addLayout(preset_layout, 4, 0, 1, 2)

        left_layout.addWidget(area_group)

        # ── Appearance ──
        app_group = QGroupBox('🎨 Appearance')
        app_layout = QGridLayout(app_group)
        app_layout.setVerticalSpacing(4)
        app_layout.setHorizontalSpacing(4)

        app_layout.addWidget(QLabel('Font size:'), 0, 0)
        self.fs_spin = QSpinBox()
        self.fs_spin.setRange(16, 120)
        self.fs_spin.setValue(50)
        self.fs_spin.valueChanged.connect(self._update_preview_from_controls)
        app_layout.addWidget(self.fs_spin, 0, 1)

        self.bold_check = QCheckBox('Bold')
        self.bold_check.setChecked(False)
        self.bold_check.stateChanged.connect(self._update_preview_from_controls)
        app_layout.addWidget(self.bold_check, 0, 2)

        app_layout.addWidget(QLabel('Highlight:'), 1, 0)
        self.h_color_btn = QPushButton()
        self.h_color_btn.setFixedHeight(28)
        self._h_color = QColor('#FFD700')
        self._update_color_btn(self.h_color_btn, self._h_color)
        self.h_color_btn.clicked.connect(lambda: self._pick_color('highlight'))
        app_layout.addWidget(self.h_color_btn, 1, 1)

        app_layout.addWidget(QLabel('Inactive:'), 2, 0)
        self.u_color_btn = QPushButton()
        self.u_color_btn.setFixedHeight(28)
        self._u_color = QColor('#AAAAAA')
        self._update_color_btn(self.u_color_btn, self._u_color)
        self.u_color_btn.clicked.connect(lambda: self._pick_color('unhighlight'))
        app_layout.addWidget(self.u_color_btn, 2, 1)

        app_layout.addWidget(QLabel('Text BG:'), 3, 0)
        self.text_bg_btn = QPushButton()
        self.text_bg_btn.setFixedHeight(28)
        self._text_bg_color = QColor(0, 0, 0, 140)
        self._update_color_btn(self.text_bg_btn, self._text_bg_color)
        self.text_bg_btn.clicked.connect(self._pick_text_bg_color)
        app_layout.addWidget(self.text_bg_btn, 3, 1)

        left_layout.addWidget(app_group)
        left_layout.addStretch()

        # ═══ RIGHT PANE — Preview + Render ═══
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # ── Preview ──
        preview_header = QHBoxLayout()
        preview_header.addWidget(QLabel('👁️ Preview:'))
        preview_header.addStretch()
        preview_header.addWidget(QLabel('Time:'))
        self.preview_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.preview_time_slider.setRange(0, 300)
        self.preview_time_slider.setValue(5)
        self.preview_time_slider.setFixedWidth(180)
        self.preview_time_slider.valueChanged.connect(self._on_preview_time_changed)
        preview_header.addWidget(self.preview_time_slider)
        self.preview_time_label = QLabel('5s')
        self.preview_time_label.setFixedWidth(40)
        preview_header.addWidget(self.preview_time_label)

        right_layout.addLayout(preview_header)
        self.preview = TextPreview()
        right_layout.addWidget(self.preview, 1)  # stretch = 1, занимает всё место

        # ── Generate button + progress ──
        btn_layout = QHBoxLayout()
        self.gen_btn = QPushButton('🎬 Generate Video')
        self.gen_btn.setFixedHeight(36)
        self.gen_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.gen_btn.clicked.connect(self._generate)
        btn_layout.addWidget(self.gen_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(22)
        btn_layout.addWidget(self.progress_bar)

        right_layout.addLayout(btn_layout)

        # ── Log ──
        right_layout.addWidget(QLabel('📋 Log:'))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(160)
        self.log_box.setStyleSheet("background: #111; color: #ccc; font-family: monospace; font-size: 11px;")
        right_layout.addWidget(self.log_box)

        main_layout.addWidget(left)
        main_layout.addWidget(right)

    # ── Helpers ──

    def _on_audio_path_changed(self):
        path = self.audio_edit.text().strip()
        if path and os.path.exists(path):
            self.audio_file = path
            self._update_preview_from_controls()

    def _on_lrc_path_changed(self):
        path = self.lrc_edit.text().strip()
        if path and os.path.exists(path):
            self.lrc_file = path
            self._try_parse_lrc()

    def _pick_file(self, kind, edit):
        if kind == 'lrc':
            path, _ = QFileDialog.getOpenFileName(self, 'Select LRC', '', 'LRC Files (*.lrc);;All Files (*)')
        elif kind == 'audio':
            path, _ = QFileDialog.getOpenFileName(self, 'Select Audio', '', 'Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a);;All Files (*)')
        else:
            path, _ = QFileDialog.getOpenFileName(self, 'Select Image', '', 'Images (*.jpg *.jpeg *.png *.bmp *.webp);;All Files (*)')
        if path:
            edit.setText(path)
            if kind == 'lrc':
                self.lrc_file = path
                self._try_parse_lrc()
            elif kind == 'audio':
                self.audio_file = path

    def _pick_output(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Save Video', 'karaoke.mp4', 'MP4 Video (*.mp4)')
        if path:
            self.out_edit.setText(path)

    def _open_lrc_creator(self):
        """Open the LRC Creator window."""
        self.lrc_creator = LRCCreatorWindow()
        self.lrc_creator.show()

    def _try_parse_lrc(self):
        try:
            _, lines = parse_lrc(self.lrc_file)
            self.parsed_lines = lines
            self._log(f"📊 Parsed {len(lines)} lines from LRC")
            self._update_preview_from_controls()
        except Exception as e:
            self._log(f"❌ LRC parse error: {e}")

    def _apply_preset(self, vals):
        self.tx_spin.setValue(vals[0])
        self.ty_spin.setValue(vals[1])
        self.tw_spin.setValue(vals[2])
        self.th_spin.setValue(vals[3])
        self._update_preview_from_controls()

    def _update_preview_from_controls(self):
        rect = (self.tx_spin.value(), self.ty_spin.value(),
                self.tw_spin.value(), self.th_spin.value())

        bg_pil = None
        bg_path = self.bg_edit.text().strip()
        if bg_path and os.path.exists(bg_path):
            try:
                bg_pil = Image.open(bg_path).convert('RGB')
            except Exception:
                pass

        fontsize = self.fs_spin.value()
        bold = self.bold_check.isChecked()
        try:
            font_regular = ImageFont.truetype(FONT_PATH, fontsize)
        except Exception:
            font_regular = ImageFont.load_default()
        try:
            font_bold_obj = ImageFont.truetype(
                FONT_PATH_BOLD, fontsize,
                index=FONT_INDEX_BOLD if FONT_INDEX_BOLD is not None else 0,
            )
        except Exception:
            font_bold_obj = font_regular
        font = font_bold_obj if bold else font_regular

        if self.parsed_lines:
            audio_dur = 300
            audio_path = self.audio_edit.text().strip()
            if audio_path and os.path.exists(audio_path):
                try:
                    audio_dur = AudioFileClip(audio_path).duration
                except Exception:
                    pass
            _, enriched_lines = split_words_with_timing(
                self.parsed_lines, audio_dur, fontsize, font_regular, font_bold_obj,
            )
        else:
            enriched_lines = []

        text_bg = self._text_bg_color
        text_bg_rgba = (text_bg.red(), text_bg.green(), text_bg.blue(), text_bg.alpha())

        self.preview.update_preview(
            rect,
            enriched_lines,
            self._h_color.name(),
            self._u_color.name(),
            sample_t=self.preview.sample_t,
            bg_pil=bg_pil,
            fontsize=fontsize,
            bold=bold,
            font=font,
            text_bg_color=text_bg_rgba,
        )

    def _on_preview_time_changed(self, val):
        self.preview.sample_t = val
        self.preview_time_label.setText(f'{val}s')
        self._update_preview_from_controls()

    def _pick_color(self, which):
        current = self._h_color if which == 'highlight' else self._u_color
        color = QColorDialog.getColor(current, self, 'Choose Color')
        if color.isValid():
            if which == 'highlight':
                self._h_color = color
                self._update_color_btn(self.h_color_btn, color)
            else:
                self._u_color = color
                self._update_color_btn(self.u_color_btn, color)
            self._update_preview_from_controls()

    def _pick_text_bg_color(self):
        color = QColorDialog.getColor(self._text_bg_color, self, 'Text Background Color',
                                       QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self._text_bg_color = color
            r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
            self.text_bg_btn.setText(f'rgba({r},{g},{b},{a})')
            self.text_bg_btn.setStyleSheet(
                f"background: rgba({r},{g},{b},{a}); color: {'#000' if color.lightness() > 128 else '#fff'}; "
                f"font-weight: bold; border: 1px solid #555; border-radius: 4px;"
            )
            self._update_preview_from_controls()

    @staticmethod
    def _update_color_btn(btn, color):
        btn.setText(color.name())
        btn.setStyleSheet(
            f"background: {color.name()}; color: {'#000' if color.lightness() > 128 else '#fff'}; "
            f"font-weight: bold; border: 1px solid #555; border-radius: 4px;"
        )

    def _log(self, msg):
        self.log_box.append(msg)

    def _generate(self):
        # Validate
        lrc = self.lrc_edit.text().strip()
        audio = self.audio_edit.text().strip()
        output = self.out_edit.text().strip()

        if not lrc or not os.path.exists(lrc):
            QMessageBox.warning(self, 'Error', 'Select a valid LRC file.')
            return
        if not audio or not os.path.exists(audio):
            QMessageBox.warning(self, 'Error', 'Select a valid audio file.')
            return
        if not output:
            QMessageBox.warning(self, 'Error', 'Specify an output file.')
            return

        bg = self.bg_edit.text().strip()
        if bg and not os.path.exists(bg):
            QMessageBox.warning(self, 'Error', 'Background image not found.')
            return

        config = {
            'lrc_file': lrc,
            'audio_file': audio,
            'bg_image': bg if bg and os.path.exists(bg) else None,
            'output_file': output,
            'fontsize': self.fs_spin.value(),
            'tx': self.tx_spin.value(),
            'ty': self.ty_spin.value(),
            'tw': self.tw_spin.value(),
            'th': self.th_spin.value(),
            'highlight_color': self._h_color.name(),
            'unhighlighted_color': self._u_color.name(),
            'bold': self.bold_check.isChecked(),
            'text_bg_color': (
                self._text_bg_color.red(),
                self._text_bg_color.green(),
                self._text_bg_color.blue(),
                self._text_bg_color.alpha(),
            ),
        }

        self.gen_btn.setEnabled(False)
        self.gen_btn.setText('⏳ Rendering…')
        self.progress_bar.setValue(0)
        self.log_box.clear()

        self.worker = RenderWorker(config)
        self.worker.sig_log.connect(self._log)
        self.worker.sig_progress.connect(self.progress_bar.setValue)
        self.worker.sig_done.connect(self._on_finished)
        self.worker.start()

    def _on_finished(self, ok, msg):
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText('🎬 Generate Video')
        self.progress_bar.setValue(100)
        if ok:
            QMessageBox.information(self, 'Done', f'Video saved:\n{msg}')
        else:
            QMessageBox.critical(self, 'Error', f'Render failed:\n{msg}')


class LRCCreatorWindow(QMainWindow):
    """Window for creating LRC files with timestamps from audio and lyrics."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('🎵 LRC Creator')
        self.setMinimumSize(900, 700)

        # State
        self.audio_file = ''
        self.lyrics_lines = []
        self.timestamps = {}  # line_index -> {'start': time, 'end': time}
        self.current_line = 0
        self.is_recording_start = True

        # Audio player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

        # Timer for updating position display
        self.position_timer = QTimer(self)
        self.position_timer.timeout.connect(self._update_position_display)
        self.position_timer.start(100)  # Update every 100ms

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)

        # ═══ TOP: File loading ═══
        file_group = QGroupBox('📂 Files')
        file_layout = QGridLayout(file_group)

        file_layout.addWidget(QLabel('Audio:'), 0, 0)
        self.audio_edit = QLineEdit()
        self.audio_edit.setPlaceholderText('Select MP3/audio file...')
        file_layout.addWidget(self.audio_edit, 0, 1)
        self.audio_btn = QPushButton('Browse')
        self.audio_btn.clicked.connect(self._load_audio_file)
        file_layout.addWidget(self.audio_btn, 0, 2)

        file_layout.addWidget(QLabel('Output:'), 1, 0)
        self.output_edit = QLineEdit('song.lrc')
        file_layout.addWidget(self.output_edit, 1, 1)
        self.output_btn = QPushButton('Browse')
        self.output_btn.clicked.connect(self._pick_output_file)
        file_layout.addWidget(self.output_btn, 1, 2)

        main_layout.addWidget(file_group)

        # ═══ MIDDLE: Lyrics input ═══
        lyrics_group = QGroupBox('📝 Lyrics')
        lyrics_layout = QVBoxLayout(lyrics_group)

        self.lyrics_text = QTextEdit()
        self.lyrics_text.setPlaceholderText(
            'Paste lyrics here (one line per stanza)...\n\n'
            'Example:\n'
            'Hello world, this is my song\n'
            'Singing in the rain\n'
            'Dancing in the moonlight'
        )
        self.lyrics_text.setMaximumHeight(150)
        lyrics_layout.addWidget(self.lyrics_text)

        self.parse_btn = QPushButton('📝 Parse Lyrics')
        self.parse_btn.setFixedHeight(32)
        self.parse_btn.clicked.connect(self._parse_lyrics)
        lyrics_layout.addWidget(self.parse_btn)

        main_layout.addWidget(lyrics_group)

        # ═══ TIMELINE: Line list with timestamps ═══
        timeline_group = QGroupBox('⏱️ Timeline')
        timeline_layout = QVBoxLayout(timeline_group)

        # Info label
        self.info_label = QLabel(
            'Load audio and parse lyrics, then press SPACE to mark START times, '
            'then SPACE again to mark END times for each line.'
        )
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet('color: #aaa; font-size: 12px; padding: 4px;')
        timeline_layout.addWidget(self.info_label)

        # Transport controls
        transport_layout = QHBoxLayout()
        self.play_btn = QPushButton('▶ Play')
        self.play_btn.setFixedHeight(32)
        self.play_btn.clicked.connect(self._toggle_play)
        self.play_btn.setEnabled(False)
        transport_layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton('⏹ Stop')
        self.stop_btn.setFixedHeight(32)
        self.stop_btn.clicked.connect(self._stop_audio)
        self.stop_btn.setEnabled(False)
        transport_layout.addWidget(self.stop_btn)

        # Position slider
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.position_slider.sliderMoved.connect(self._seek_audio)
        transport_layout.addWidget(self.position_slider, 1)

        self.time_label = QLabel('0:00 / 0:00')
        self.time_label.setFixedWidth(100)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        transport_layout.addWidget(self.time_label)

        timeline_layout.addLayout(transport_layout)

        # Lines list
        self.lines_list = QListWidget()
        self.lines_list.setAlternatingRowColors(True)
        self.lines_list.setStyleSheet('font-size: 13px;')
        timeline_layout.addWidget(self.lines_list)

        # Mark controls
        mark_layout = QHBoxLayout()
        self.mark_btn = QPushButton('⏱ Mark [SPACE]')
        self.mark_btn.setFixedHeight(40)
        self.mark_btn.setStyleSheet('font-size: 14px; font-weight: bold;')
        self.mark_btn.clicked.connect(self._mark_timestamp)
        self.mark_btn.setEnabled(False)
        mark_layout.addWidget(self.mark_btn, 1)

        self.undo_btn = QPushButton('↩ Undo [Backspace]')
        self.undo_btn.setFixedHeight(40)
        self.undo_btn.clicked.connect(self._undo_last_timestamp)
        self.undo_btn.setEnabled(False)
        mark_layout.addWidget(self.undo_btn)

        self.reset_btn = QPushButton('🔄 Reset All')
        self.reset_btn.setFixedHeight(40)
        self.reset_btn.clicked.connect(self._reset_timestamps)
        mark_layout.addWidget(self.reset_btn)

        timeline_layout.addLayout(mark_layout)

        main_layout.addWidget(timeline_group, 1)  # Stretch to fill space

        # ═══ BOTTOM: Save button ═══
        save_layout = QHBoxLayout()
        save_layout.addStretch()

        self.save_btn = QPushButton('💾 Save LRC')
        self.save_btn.setFixedHeight(40)
        self.save_btn.setStyleSheet('font-size: 14px; font-weight: bold;')
        self.save_btn.clicked.connect(self._save_lrc)
        self.save_btn.setEnabled(False)
        save_layout.addWidget(self.save_btn)

        main_layout.addLayout(save_layout)

        # Keyboard shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        from PyQt6.QtGui import QShortcut, QKeySequence

        # Space bar for marking timestamps
        space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        space_shortcut.activated.connect(self._mark_timestamp)

        # Backspace for undoing last timestamp
        backspace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self)
        backspace_shortcut.activated.connect(self._undo_last_timestamp)

    def _load_audio_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select Audio', '',
            'Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac);;All Files (*)'
        )
        if path:
            self.audio_edit.setText(path)
            self.audio_file = path
            self.player.setSource(QUrl.fromLocalFile(path))
            self.play_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self._update_info(f'✅ Loaded: {os.path.basename(path)}')

    def _pick_output_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save LRC', 'song.lrc', 'LRC Files (*.lrc);;All Files (*)'
        )
        if path:
            self.output_edit.setText(path)

    def _parse_lyrics(self):
        text = self.lyrics_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, 'Error', 'Please enter some lyrics first.')
            return

        # Split into lines, filter empty
        self.lyrics_lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not self.lyrics_lines:
            QMessageBox.warning(self, 'Error', 'No valid lyrics lines found.')
            return

        # Update list widget
        self.lines_list.clear()
        for i, line in enumerate(self.lyrics_lines):
            item = QListWidgetItem(f'Line {i+1}: {line}')
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.lines_list.addItem(item)

        self.timestamps = {}
        self.current_line = 0
        self.is_recording_start = True
        self._update_list_display()
        self.mark_btn.setEnabled(True)
        self.undo_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self._update_info(f'✅ Parsed {len(self.lyrics_lines)} lines. Press PLAY, then SPACE to mark timestamps.')

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_btn.setText('▶ Play')
        else:
            self.player.play()
            self.play_btn.setText('⏸ Pause')

    def _stop_audio(self):
        self.player.stop()
        self.play_btn.setText('▶ Play')

    def _update_position_display(self):
        if not self.audio_file:
            return

        duration = self.player.duration()  # milliseconds
        position = self.player.position()

        if duration > 0:
            # Update slider
            self.position_slider.blockSignals(True)
            self.position_slider.setValue(int((position / duration) * 1000))
            self.position_slider.blockSignals(False)

            # Update time label
            pos_str = self._format_time_ms(position)
            dur_str = self._format_time_ms(duration)
            self.time_label.setText(f'{pos_str} / {dur_str}')

    def _format_time_ms(self, ms):
        """Format milliseconds to M:SS.S format."""
        total_seconds = ms / 1000.0
        minutes = int(total_seconds // 60)
        seconds = total_seconds - minutes * 60
        return f'{minutes}:{seconds:05.2f}'

    def _seek_audio(self, position):
        if self.audio_file:
            duration = self.player.duration()
            if duration > 0:
                self.player.setPosition(int((position / 1000.0) * duration))

    def _mark_timestamp(self):
        if not self.audio_file or not self.lyrics_lines:
            QMessageBox.warning(self, 'Error', 'Load audio and parse lyrics first.')
            return

        if self.current_line >= len(self.lyrics_lines):
            self._update_info('✅ All lines have been marked! You can save the LRC file now.')
            return

        current_time_ms = self.player.position()
        current_time_sec = current_time_ms / 1000.0

        if self.is_recording_start:
            # Mark start time
            if self.current_line not in self.timestamps:
                self.timestamps[self.current_line] = {}
            self.timestamps[self.current_line]['start'] = current_time_sec
            self.is_recording_start = False
            self._update_info(f'⏱️ Line {self.current_line + 1} START: {self._format_time_sec(current_time_sec)}')
        else:
            # Mark end time
            self.timestamps[self.current_line]['end'] = current_time_sec

            # Validate
            if self.timestamps[self.current_line]['end'] <= self.timestamps[self.current_line]['start']:
                QMessageBox.warning(self, 'Error', 'End time must be after start time. Try again.')
                del self.timestamps[self.current_line]['end']
                return

            self.is_recording_start = True
            self.current_line += 1
            self._update_info(
                f'⏱️ Line {self.current_line} END: {self._format_time_sec(current_time_sec)}\n'
                f'Next: Line {self.current_line + 1} (if exists)'
            )

        self._update_list_display()

        # Check if all lines are done
        if self.current_line >= len(self.lyrics_lines):
            self._update_info('✅ All lines marked! You can now save the LRC file.')
            self.mark_btn.setEnabled(False)
            self.undo_btn.setEnabled(True)  # Still allow undo even when all done

    def _format_time_sec(self, seconds):
        """Format seconds to [mm:ss.xx] LRC format."""
        minutes = int(seconds // 60)
        secs = seconds - minutes * 60
        return f'[{minutes:02d}:{secs:05.2f}]'

    def _update_list_display(self):
        """Update the lines list with timestamp information."""
        for i in range(self.lines_list.count()):
            item = self.lines_list.item(i)
            line_idx = i
            line_text = self.lyrics_lines[line_idx]

            if line_idx in self.timestamps:
                ts = self.timestamps[line_idx]
                start_str = self._format_time_sec(ts.get('start', 0))
                end_str = self._format_time_sec(ts.get('end', 0)) if 'end' in ts else '[??:??.??]'

                if line_idx == self.current_line and not self.is_recording_start:
                    # Waiting for end time - light yellow background, black text
                    item.setText(f'▶ {line_idx+1}: {line_text}\n   START: {start_str} | END: {end_str} (waiting...)')
                    item.setBackground(QColor(255, 255, 200))
                    item.setForeground(QColor(0, 0, 0))
                elif line_idx == self.current_line and self.is_recording_start:
                    # Waiting for start time - light blue background, black text
                    item.setText(f'▶ {line_idx+1}: {line_text}\n   START: [next] | END: [next]')
                    item.setBackground(QColor(200, 230, 255))
                    item.setForeground(QColor(0, 0, 0))
                else:
                    # Completed line - light green background, black text
                    item.setText(f'✅ {line_idx+1}: {line_text}\n   {start_str} → {end_str}')
                    item.setBackground(QColor(210, 240, 210))
                    item.setForeground(QColor(0, 0, 0))
            else:
                if line_idx == self.current_line:
                    # Current line waiting for start - light blue, black text
                    item.setText(f'▶ {line_idx+1}: {line_text}\n   [waiting for START timestamp]')
                    item.setBackground(QColor(200, 230, 255))
                    item.setForeground(QColor(0, 0, 0))
                else:
                    # Future line - light gray background, black text
                    item.setText(f'⏳ {line_idx+1}: {line_text}')
                    item.setBackground(QColor(235, 235, 235))
                    item.setForeground(QColor(0, 0, 0))

        # Auto-scroll to current line
        if self.current_line < self.lines_list.count():
            self.lines_list.scrollToItem(self.lines_list.item(self.current_line), QListWidget.ScrollHint.EnsureVisible)

    def _undo_last_timestamp(self):
        """Undo the last timestamp (Backspace)."""
        if not self.lyrics_lines:
            return

        if self.current_line == 0 and self.is_recording_start:
            self._update_info('ℹ️ Nothing to undo.')
            self.undo_btn.setEnabled(False)
            return

        if not self.is_recording_start:
            # Currently waiting for END time → remove START for current line
            if self.current_line in self.timestamps:
                del self.timestamps[self.current_line]
                self.is_recording_start = True
                self._update_info(f'↩️ Undid START for line {self.current_line + 1}')
        else:
            # Waiting for START time → go back to previous line
            self.current_line -= 1
            if self.current_line in self.timestamps:
                # If previous line had both START and END, remove END
                if 'end' in self.timestamps[self.current_line]:
                    del self.timestamps[self.current_line]['end']
                    self.is_recording_start = False
                    self._update_info(f'↩️ Undid END for line {self.current_line + 1}')
                else:
                    # Remove START and go back one more
                    del self.timestamps[self.current_line]
                    self.current_line -= 1
                    self.is_recording_start = True
                    if self.current_line < 0:
                        self.current_line = 0
                    self._update_info(f'↩️ Undid line {self.current_line + 2}')
            else:
                self.is_recording_start = True
                self._update_info(f'↩️ Back to line {self.current_line + 1}')

        # Re-enable mark button if it was disabled
        self.mark_btn.setEnabled(True)
        self.undo_btn.setEnabled(True)
        self._update_list_display()

    def _reset_timestamps(self):
        reply = QMessageBox.question(
            self, 'Reset', 'Reset all timestamps?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.timestamps = {}
            self.current_line = 0
            self.is_recording_start = True
            self._update_list_display()
            self.mark_btn.setEnabled(True)
            self._update_info('🔄 All timestamps reset.')

    def _save_lrc(self):
        output_path = self.output_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, 'Error', 'Specify an output file path.')
            return

        # Validate all lines have timestamps
        if len(self.timestamps) < len(self.lyrics_lines):
            reply = QMessageBox.question(
                self, 'Incomplete',
                f'Only {len(self.timestamps)}/{len(self.lyrics_lines)} lines have timestamps.\n'
                'Save anyway?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Generate LRC content
        lrc_lines = []
        for i in range(len(self.lyrics_lines)):
            if i in self.timestamps:
                ts = self.timestamps[i]
                start_tag = self._format_time_sec(ts['start'])
                end_tag = self._format_time_sec(ts['end']) if 'end' in ts else ''
                lrc_lines.append(f'{start_tag}{end_tag}{self.lyrics_lines[i]}')
            else:
                # Lines without timestamps
                lrc_lines.append(self.lyrics_lines[i])

        # Write to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lrc_lines))
            QMessageBox.information(self, 'Success', f'LRC file saved:\n{output_path}')
            self._update_info(f'✅ Saved: {output_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to save:\n{e}')

    def _update_info(self, msg):
        self.info_label.setText(msg)

    def closeEvent(self, event):
        """Clean up resources when window is closed."""
        self.position_timer.stop()
        self.player.stop()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 45))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 230))
    palette.setColor(QPalette.ColorRole.Base, QColor(20, 20, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 60))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(220, 220, 230))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 220, 230))
    palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 230))
    palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 70))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 230))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Link, QColor(100, 160, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(60, 100, 180))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
