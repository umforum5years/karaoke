import re
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoClip, AudioFileClip

FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"


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
    for match in re.finditer(r'\[(\d+):(\d+\.\d+)\](.*)', content):
        time_sec = int(match.group(1)) * 60 + float(match.group(2))
        text = match.group(3).strip()
        if text:
            lines.append({'time': time_sec, 'text': text})

    lines.sort(key=lambda x: x['time'])
    return metadata, lines


def split_words_with_timing(lines, audio_duration):
    word_timeline = []
    for i, line in enumerate(lines):
        next_time = lines[i + 1]['time'] if i + 1 < len(lines) else audio_duration
        line_duration = max(next_time - line['time'], 1.0)
        words = line['text'].split()
        if not words:
            continue
        word_dur = line_duration / len(words)
        for j, word in enumerate(words):
            w_start = line['time'] + j * word_dur
            w_end = w_start + word_dur
            word_timeline.append({
                'text': word,
                'start': w_start,
                'end': w_end,
                'line_time': line['time'],
            })
    return word_timeline


def load_background_image(image_path, video_size):
    """Load and resize background image to fit video size."""
    img = Image.open(image_path).convert('RGB')
    img = img.resize(video_size, Image.LANCZOS)
    return img


def render_frame(t, width, height, word_timeline, lines, fontsize, font,
                 text_rect=None, bg_image=None):
    """Render a single frame with karaoke text at time t.

    text_rect — (x, y, w, h) area where text is drawn.
    bg_image  — PIL Image used as background (reused each frame).
    """
    if bg_image is not None:
        img = bg_image.copy()
    else:
        img = Image.new('RGB', (width, height), (20, 20, 30))

    draw = ImageDraw.Draw(img)

    # Default text area: entire frame with margins
    if text_rect is None:
        margin = 60
        text_rect = (margin, margin, width - 2 * margin, height - 2 * margin)

    rx, ry, rw, rh = text_rect

    # Group lines into screens of 4
    lines_per_screen = 4

    for group_start in range(0, len(lines), lines_per_screen):
        group = lines[group_start:group_start + lines_per_screen]
        first_time = group[0]['time'] if group else 0
        next_first = lines[group_start + lines_per_screen]['time'] if group_start + lines_per_screen < len(lines) else first_time + 10

        # Show this group from its first line's time until the next group starts
        show_start = first_time
        show_end = next_first

        if t < show_start or t >= show_end:
            continue

        # Calculate vertical positions inside the text rect
        total_height = len(group) * (fontsize + 20)
        start_y = ry + (rh - total_height) // 2

        for line_idx, line in enumerate(group):
            y = start_y + line_idx * (fontsize + 20)
            words = line['text'].split()
            if not words:
                continue

            # Measure all words to center the line inside rect
            word_widths = []
            for word in words:
                bbox = font.getbbox(word)
                w = bbox[2] - bbox[0]
                word_widths.append(w)

            total_width = sum(word_widths) + 10 * (len(words) - 1)
            x = rx + (rw - total_width) // 2

            # Draw semi-transparent dark rectangle behind text line for readability
            draw.rounded_rectangle(
                [x - 10, y - 4, x + total_width + 10, y + fontsize + 4],
                radius=8,
                fill=(0, 0, 0, 120),
            )

            # Draw each word with gradual fill
            for word_idx, word in enumerate(words):
                ww = word_widths[word_idx]

                # Find this word's timing info
                word_start = None
                word_dur = None
                for wt in word_timeline:
                    if wt['text'] == word and abs(wt['line_time'] - line['time']) < 0.01:
                        word_start = wt['start']
                        word_dur = wt['end'] - wt['start']
                        break

                # Calculate fill ratio
                fill_ratio = 0.0
                if word_start is not None:
                    elapsed = t - word_start
                    if word_dur and word_dur > 0:
                        fill_ratio = min(max(elapsed / word_dur, 0.0), 1.0)
                    elif elapsed > 0:
                        fill_ratio = 1.0

                if fill_ratio <= 0:
                    draw.text((x, y), word, fill='#AAAAAA', font=font)
                elif fill_ratio >= 1:
                    draw.text((x, y), word, fill='#FFD700', font=font)
                else:
                    # Partial fill
                    draw.text((x, y), word, fill='#AAAAAA', font=font)
                    highlight_img = Image.new('RGBA', (ww, fontsize + 10), (0, 0, 0, 0))
                    hl_draw = ImageDraw.Draw(highlight_img)
                    hl_draw.text((0, 0), word, fill='#FFD700', font=font)
                    fill_w = int(ww * fill_ratio)
                    if fill_w > 0:
                        highlight_img = highlight_img.crop((0, 0, fill_w, highlight_img.height))
                        img.paste(highlight_img, (x, y), highlight_img)

                x += ww + 10

    return np.array(img)


def create_karaoke_video(lrc_file, audio_file, output_video,
                         fontsize=50, bg_image_path=None, text_rect=None):
    print("📝 Parsing LRC...")
    metadata, lines = parse_lrc(lrc_file)
    print(f"📊 {len(lines)} lines")

    print("🎬 Loading audio...")
    audio = AudioFileClip(audio_file)
    duration = audio.duration
    print(f"⏱️ Duration: {duration:.2f}s")

    print("⏱️ Calculating word timing...")
    word_timeline = split_words_with_timing(lines, duration)

    print("🖊️ Loading font...")
    font = ImageFont.truetype(FONT_PATH, fontsize)

    width, height = 1280, 720

    # Background image
    bg_pil = None
    if bg_image_path and os.path.exists(bg_image_path):
        print(f"🖼️ Loading background image: {bg_image_path}")
        bg_pil = load_background_image(bg_image_path, (width, height))
    else:
        print("🎨 No background image, using solid color")

    if text_rect:
        print(f"📐 Text area: x={text_rect[0]}, y={text_rect[1]}, w={text_rect[2]}, h={text_rect[3]}")
    else:
        print("📐 Text area: full frame (auto-margins)")

    def make_frame(t):
        return render_frame(t, width, height, word_timeline, lines, fontsize, font,
                            text_rect=text_rect, bg_image=bg_pil)

    print(f"📹 Creating video ({duration:.0f}s at 30fps)...")
    video = VideoClip(make_frame, duration=duration)
    video = video.with_audio(audio)

    print(f"💾 Rendering {output_video}...")
    video.write_videofile(
        output_video,
        fps=30,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        bitrate='5000k',
        audio_bitrate='192k',
    )

    video.close()
    audio.close()
    print(f"\n✅ Done! → {output_video}")


if __name__ == '__main__':
    print("=" * 60)
    print("🎤 LRC to Karaoke Video")
    print("=" * 60)

    # === SETTINGS ===
    LRC_FILE = 'song.lrc'
    AUDIO_FILE = 'song.mp3'
    OUTPUT_FILE = 'karaoke.mp4'
    FONT_SIZE = 50

    # Background image (set to None to use solid color)
    BG_IMAGE = 'background.jpg'  # e.g. 'background.jpg'

    # Text rectangle: (x, y, width, height) — area where lyrics appear
    # Set to None to use the full frame with auto margins
    TEXT_RECT = (200, 100, 800, 500)  # bottom band example

    create_karaoke_video(
        LRC_FILE,
        AUDIO_FILE,
        OUTPUT_FILE,
        fontsize=FONT_SIZE,
        bg_image_path=BG_IMAGE,
        text_rect=TEXT_RECT,
    )
