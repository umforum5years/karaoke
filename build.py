#!/usr/bin/env python3
"""
Build script for Karaoke Video Maker app.
Creates standalone executable for macOS or Windows using PyInstaller.

Usage:
    python build.py           # Build for current platform
    python build.py --clean   # Clean build (remove cache)
"""
import sys
import os
import platform
import subprocess
import shutil


def main():
    clean = '--clean' in sys.argv

    system = platform.system()

    if system == 'Darwin':
        build_macos(clean)
    elif system == 'Windows':
        build_windows(clean)
    else:
        print(f"❌ Unsupported platform: {system}")
        sys.exit(1)


def build_macos(clean):
    app_name = 'KaraokeVideoMaker'
    script = 'karaoke_app.py'
    icon_mac = None

    # Check for macOS icon
    if os.path.exists('icon.icns'):
        icon_mac = 'icon.icns'
    elif os.path.exists('icon.png'):
        icon_mac = 'icon.png'

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', app_name,
        '--onedir',
        '--windowed',
        '--noconfirm',
        '--collect-all', 'moviepy',
        '--collect-all', 'proglog',
        '--collect-all', 'PIL',
        '--collect-all', 'numpy',
        '--collect-all', 'imageio',
        '--hidden-import', 'PyQt6',
        '--hidden-import', 'moviepy',
        '--hidden-import', 'moviepy.audio',
        '--hidden-import', 'moviepy.audio.fx',
        '--hidden-import', 'moviepy.audio.AudioClip',
        '--hidden-import', 'moviepy.audio.io',
        '--hidden-import', 'moviepy.audio.io.AudioFileClip',
        '--hidden-import', 'moviepy.video',
        '--hidden-import', 'moviepy.video.fx',
        '--hidden-import', 'moviepy.video.io',
        '--hidden-import', 'moviepy.video.io.ffmpeg_writer',
        '--hidden-import', 'moviepy.decorators',
        '--hidden-import', 'proglog',
        '--hidden-import', 'PIL',
        '--hidden-import', 'numpy',
        '--hidden-import', 'imageio',
        '--hidden-import', 'imageio_ffmpeg',
    ]

    if icon_mac:
        cmd.extend(['--icon', icon_mac])

    if clean:
        cmd.append('--clean')

    cmd.append(script)

    print("🍎 Building for macOS...")
    print(f"Command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    print("\n✅ Build complete!")
    print(f"📁 App location: dist/{app_name}.app")
    print(f"\nTo run: open dist/{app_name}.app")


def build_windows(clean):
    app_name = 'KaraokeVideoMaker'
    script = 'karaoke_app.py'
    icon_win = None

    # Check for Windows icon
    if os.path.exists('icon.ico'):
        icon_win = 'icon.ico'

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', app_name,
        '--onedir',
        '--noconsole',
        '--noconfirm',
        # Bundle fonts folder
        '--add-data', 'fonts/DejaVuSans.ttf;fonts',
        '--add-data', 'fonts/DejaVuSans-Bold.ttf;fonts',
        # Bundle background image if exists
        # Collect all dependencies
        '--collect-all', 'moviepy',
        '--collect-all', 'proglog',
        '--collect-all', 'PIL',
        '--collect-all', 'numpy',
        '--collect-all', 'imageio',
        '--collect-all', 'PyQt6',
        '--collect-submodules', 'moviepy.audio.fx.all',
        '--collect-submodules', 'moviepy.video.fx.all',
        # Hidden imports for PyQt6
        '--hidden-import', 'PyQt6',
        '--hidden-import', 'PyQt6.QtCore',
        '--hidden-import', 'PyQt6.QtGui',
        '--hidden-import', 'PyQt6.QtWidgets',
        '--hidden-import', 'PyQt6.sip',
        # Hidden imports for moviepy
        '--hidden-import', 'moviepy',
        '--hidden-import', 'moviepy.audio',
        '--hidden-import', 'moviepy.audio.fx',
        '--hidden-import', 'moviepy.audio.fx.all',
        '--hidden-import', 'moviepy.audio.AudioClip',
        '--hidden-import', 'moviepy.audio.io',
        '--hidden-import', 'moviepy.audio.io.AudioFileClip',
        '--hidden-import', 'moviepy.audio.io.readers',
        '--hidden-import', 'moviepy.video',
        '--hidden-import', 'moviepy.video.fx',
        '--hidden-import', 'moviepy.video.fx.all',
        '--hidden-import', 'moviepy.video.io',
        '--hidden-import', 'moviepy.video.io.ffmpeg_writer',
        '--hidden-import', 'moviepy.video.io.VideoFileClip',
        '--hidden-import', 'moviepy.decorators',
        '--hidden-import', 'moviepy.config',
        '--hidden-import', 'moviepy.tools',
        # Other dependencies
        '--hidden-import', 'proglog',
        '--hidden-import', 'PIL',
        '--hidden-import', 'PIL.ImageFont',
        '--hidden-import', 'numpy',
        '--hidden-import', 'imageio',
        '--hidden-import', 'imageio_ffmpeg',
        '--hidden-import', 'imageio.plugins',
        '--hidden-import', 'imageio.plugins.ffmpeg',
        # Include scipy if present
        '--hidden-import', 'scipy',
        '--hidden-import', 'scipy.interpolate',
    ]

    if icon_win:
        cmd.extend(['--icon', icon_win])

    if clean:
        cmd.append('--clean')

    cmd.append(script)

    print("🪟 Building for Windows...")
    print(f"Command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    print("\n✅ Build complete!")
    print(f"📁 App location: dist\\{app_name}\\{app_name}.exe")
    print(f"\nTo run: dist\\{app_name}\\{app_name}.exe")


if __name__ == '__main__':
    main()
