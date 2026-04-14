# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('fonts/DejaVuSans.ttf', 'fonts'), ('fonts/DejaVuSans-Bold.ttf', 'fonts')]
binaries = []
hiddenimports = ['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.sip', 'moviepy', 'moviepy.audio', 'moviepy.audio.fx', 'moviepy.audio.fx.all', 'moviepy.audio.AudioClip', 'moviepy.audio.io', 'moviepy.audio.io.AudioFileClip', 'moviepy.audio.io.readers', 'moviepy.video', 'moviepy.video.fx', 'moviepy.video.fx.all', 'moviepy.video.io', 'moviepy.video.io.ffmpeg_writer', 'moviepy.video.io.VideoFileClip', 'moviepy.decorators', 'moviepy.config', 'moviepy.tools', 'proglog', 'PIL', 'PIL.ImageFont', 'numpy', 'imageio', 'imageio_ffmpeg', 'imageio.plugins', 'imageio.plugins.ffmpeg', 'scipy', 'scipy.interpolate']
hiddenimports += collect_submodules('moviepy.audio.fx.all')
hiddenimports += collect_submodules('moviepy.video.fx.all')
tmp_ret = collect_all('moviepy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('proglog')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('imageio')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['karaoke_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KaraokeVideoMaker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KaraokeVideoMaker',
)
