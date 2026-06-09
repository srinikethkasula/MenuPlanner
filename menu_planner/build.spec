# build.spec — PyInstaller spec for MenuPlanner
# Run from menu_planner/ directory:
#   pip install pyinstaller
#   pyinstaller build.spec

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

pptx_datas, pptx_binaries, pptx_hiddenimports = collect_all('pptx')
lxml_datas, lxml_binaries, lxml_hiddenimports = collect_all('lxml')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=pptx_binaries + lxml_binaries,
    datas=[
        # Slide backgrounds
        ('resources/bg_good_morning.png', 'resources'),
        ('resources/bg_dish_slide.png',   'resources'),
        ('resources/bg_closing.png',      'resources'),
        # Placeholder company images (user replaces via Settings)
        ('resources/company_image.jpg',   'resources'),
        ('resources/team_photo.jpg',      'resources'),
        ('resources/template.pptx',       'resources'),
        ('data/menu_planner.db',          'resources'),
        # ALL dish images baked in as seed
        ('data/dish_images',              '_seed_images'),
    ] + pptx_datas + lxml_datas,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtSvg',
        'PyQt6.Qt6.plugins.platforms.qwindows',
        'PyQt6.Qt6.plugins.imageformats.qjpeg',
        'PyQt6.Qt6.plugins.imageformats.qpng',
        'PyQt6.Qt6.plugins.imageformats.qwebp',
        'PyQt6.Qt6.plugins.styles.qwindowsvistastyle',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.cell._writer',
        'openpyxl.worksheet._writer',
        'et_xmlfile',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PIL.JpegImagePlugin',
        'PIL.PngImagePlugin',
        'requests',
        'certifi',
        'charset_normalizer',
        'charset_normalizer.md__mypyc',
        'urllib',
        'urllib.request',
        'urllib.parse',
        'sqlite3',
        'json',
        'logging',
        'logging.handlers',
        'difflib',
        'shutil',
        'pathlib',
    ] + pptx_hiddenimports + lxml_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MenuPlanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window (windowed app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico',
)
