# LRC Creator - Feature Showcase

## 🎯 What is it?

A built-in tool for creating synchronized lyric files (.lrc) from audio and plain text.

## 🎬 Workflow Demo

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: Load Audio File                                │
│  ┌──────────────────────────────────────────┐           │
│  │ Audio: [song.mp3              ] [Browse] │           │
│  │ Output: [song.lrc             ] [Browse] │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Step 2: Enter Lyrics                                   │
│  ┌──────────────────────────────────────────┐           │
│  │ Hello world, this is my song             │           │
│  │ Singing in the rain                      │           │
│  │ Dancing in the moonlight                 │           │
│  └──────────────────────────────────────────┘           │
│         [📝 Parse Lyrics]                               │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Step 3: Mark Timestamps                                │
│  ┌──────────────────────────────────────────┐           │
│  │ [▶ Play] [⏹ Stop] [====|======] 1:23/3:45│           │
│  ├──────────────────────────────────────────┤           │
│  │ ✅ 1: Hello world, this is my song       │           │
│  │    [00:12.50] → [00:18.75]               │           │
│  ├──────────────────────────────────────────┤           │
│  │ ▶ 2: Singing in the rain                 │           │
│  │    [waiting for START timestamp]         │ ← SPACE!  │
│  ├──────────────────────────────────────────┤           │
│  │ ⏳ 3: Dancing in the moonlight            │           │
│  └──────────────────────────────────────────┘           │
│         [⏱ Mark [SPACE]] [🔄 Reset All]                 │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Step 4: Save LRC File                                  │
│         [💾 Save LRC]                                   │
│                                                         │
│  Result: song.lrc                                       │
│  [00:12.50]Hello world, this is my song                 │
│  [00:18.75]Singing in the rain                          │
│  [00:24.30]Dancing in the moonlight                     │
└─────────────────────────────────────────────────────────┘
```

## 🎨 Visual States

| State | Color | Meaning |
|-------|-------|---------|
| ⏳ Pending | Default | Waiting to be marked |
| 🔵 Current | Blue | Ready for START timestamp |
| 🟡 In Progress | Yellow | START marked, waiting for END |
| ✅ Complete | Green | Both START and END marked |

## ⌨️ Controls

### Keyboard
- **SPACE**: Mark timestamp (works globally)

### Mouse
- **▶ Play / ⏸ Pause**: Toggle playback
- **⏹ Stop**: Stop playback
- **Slider**: Seek to position
- **⏱ Mark**: Same as SPACE
- **🔄 Reset All**: Clear all timestamps
- **💾 Save LRC**: Export to file

## 📊 Output Format

```lrc
[00:12.50]Hello world, this is my song
[00:18.75]Singing in the rain
[00:24.30]Dancing in the moonlight
```

## 🔄 Integration with Main App

```
LRC Creator                    Main Karaoke App
┌──────────────┐              ┌──────────────────┐
│ Audio + Text │  ─────────>  │ Generate .lrc    │
│ Mark timing  │  SAVE        │ Load .lrc file   │
│ Save .lrc    │  ─────────>  │ Create video     │
└──────────────┘              └──────────────────┘
```

## 💡 Use Cases

1. **Karaoke Enthusiasts**: Create synchronized lyrics for your favorite songs
2. **Content Creators**: Make karaoke videos for YouTube/social media
3. **Musicians**: Add professional lyrics timing to your tracks
4. **Language Learning**: Create timed lyrics for language practice

## ✨ Key Features

- ✅ Real-time audio playback
- ✅ Visual feedback for each line
- ✅ Space bar for quick marking
- ✅ Seek and pause support
- ✅ Reset and retry functionality
- ✅ Partial save support
- ✅ Compatible with standard LRC format
- ✅ Direct integration with main app

## 🚀 Getting Started

1. Open `karaoke_app.py`
2. Click **"🎵 Create LRC File (from audio + lyrics)"**
3. Follow the 4-step workflow
4. Use your .lrc file in the main app!

---

For detailed instructions, see [LRC_CREATOR_GUIDE.md](LRC_CREATOR_GUIDE.md)
