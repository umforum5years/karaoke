#!/usr/bin/env python3
"""Generate .ico and .icns icon files from icon.jpeg."""
import os
import subprocess
from PIL import Image

ICON_SRC = 'icon.jpeg'
ICO_OUT = 'icon.ico'
ICNS_OUT = 'icon.icns'


def generate_ico(src, dst):
    """Generate Windows .ico with multiple sizes."""
    img = Image.open(src)
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64),
             (128, 128), (256, 256)]
    img.save(dst, format='ICO', sizes=sizes)
    print(f"✅ {dst} generated")


def generate_icns(src, dst):
    """Generate macOS .icns using iconutil."""
    img = Image.open(src)

    # Create temporary iconset directory
    iconset = 'icon.iconset'
    os.makedirs(iconset, exist_ok=True)

    # macOS icon sizes
    mac_sizes = {
        'icon_16x16.png': 16,
        'icon_16x16@2x.png': 32,
        'icon_32x32.png': 32,
        'icon_32x32@2x.png': 64,
        'icon_128x128.png': 128,
        'icon_128x128@2x.png': 256,
        'icon_256x256.png': 256,
        'icon_256x256@2x.png': 512,
        'icon_512x512.png': 512,
        'icon_512x512@2x.png': 1024,
    }

    for name, size in mac_sizes.items():
        resized = img.resize((size, size), Image.LANCZOS)
        resized.save(os.path.join(iconset, name))

    # Convert to .icns using iconutil
    subprocess.run(['iconutil', '-c', 'icns', '-o', dst, iconset], check=True)

    # Cleanup
    subprocess.run(['rm', '-rf', iconset], check=True)
    print(f"✅ {dst} generated")


if __name__ == '__main__':
    if not os.path.exists(ICON_SRC):
        print(f"❌ {ICON_SRC} not found")
        exit(1)

    generate_ico(ICON_SRC, ICO_OUT)
    generate_icns(ICON_SRC, ICNS_OUT)
    print("\n✅ Done! Place icon.ico/icon.icns in project root for build.py to use.")
