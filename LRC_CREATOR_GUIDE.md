# 🎵 LRC Creator Guide

## Overview
The LRC Creator is a new feature in the Karaoke Video Maker that allows you to create synchronized lyrics files (.lrc) from audio files and plain text lyrics.

## How to Use

### 1. Launch LRC Creator
- Open the main Karaoke Video Maker application
- Click the **"🎵 Create LRC File (from audio + lyrics)"** button in the left panel

### 2. Load Audio File
- Click **Browse** next to the "Audio" field
- Select an MP3, WAV, OGG, FLAC, M4A, or AAC file
- The audio player will be ready for playback

### 3. Enter Lyrics
- Paste your lyrics in the "Lyrics" text area
- Enter one line of lyrics per line (press Enter after each line)
- Click **"📝 Parse Lyrics"** to process the text

### 4. Mark Timestamps

#### Workflow:
1. **Press PLAY** (▶) to start playing the audio
2. **Press SPACE** when you hear the first word of a line → This marks the **START** time
3. **Press SPACE** again when the line finishes → This marks the **END** time
4. The app automatically moves to the next line
5. Repeat until all lines are marked

#### Visual Feedback:
- 🔵 **Blue highlight**: Current line waiting for timestamp
- 🟡 **Yellow highlight**: Line has START marked, waiting for END
- ✅ **Green highlight**: Line fully marked with both START and END times

#### Controls:
- **SPACE**: Mark timestamp (start or end)
- **⏱ Mark button**: Same as SPACE
- **▶ Play / ⏸ Pause**: Toggle audio playback
- **⏹ Stop**: Stop playback
- **Slider**: Seek to different position in audio
- **🔄 Reset All**: Clear all timestamps and start over

### 5. Save LRC File
- Click **Browse** next to "Output" to choose where to save
- Click **"💾 Save LRC"**
- The file will be saved in standard LRC format: `[mm:ss.xx]Lyric text here`

## LRC Format Example
```
[00:12.50]Hello world, this is my song
[00:18.75]Singing in the rain
[00:24.30]Dancing in the moonlight
```

## Tips
- **Practice first**: Play the song a few times to get familiar with the timing
- **Use headphones**: Better audio clarity helps with precise timing
- **Don't rush**: You can pause the audio and take your time
- **Reset if needed**: Use the Reset All button to start over
- **Save partial work**: You can save even if not all lines are marked (with warning)

## Using the LRC File
Once created, you can:
1. Load the .lrc file in the main Karaoke Video Maker
2. Combine it with the same audio file
3. Generate a karaoke video with synchronized lyrics

## Troubleshooting

### Audio doesn't play
- Check that the audio file is a supported format
- Try converting to MP3 if using a less common format
- Ensure your system audio is working

### Timing is off
- Use the slider to seek back and check timestamps
- Reset and re-mark if needed
- Try marking at the exact moment you hear the first/last word

### Can't save
- Make sure you've selected an output file path
- At least some lines should have timestamps
- Check file permissions for the output directory

## Keyboard Shortcuts
- **SPACE**: Mark timestamp (works even when the window is not focused)

## Technical Notes
- Timestamps are stored with centisecond precision (hundredths of a second)
- The LRC format is compatible with most karaoke and lyrics display software
- Lines without timestamps will be saved without time tags
