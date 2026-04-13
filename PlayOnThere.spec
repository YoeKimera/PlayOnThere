# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_dir = Path(SPECPATH)
vlc_dir = Path(r"C:\Program Files\VideoLAN\VLC")

binaries = []
datas = []
hiddenimports = ["screeninfo", "vlc"]

icon_png = project_dir / "play_icon.png"
icon_ico = project_dir / "play_icon.ico"
if icon_png.exists():
    datas.append((str(icon_png), "."))

for dll_name in ("libvlc.dll", "libvlccore.dll"):
    dll_path = vlc_dir / dll_name
    if dll_path.exists():
        binaries.append((str(dll_path), "."))

for folder_name in ("plugins", "lua", "locale", "hrtfs", "skins"):
    folder_path = vlc_dir / folder_name
    if folder_path.exists():
        datas.append((str(folder_path), folder_name))


a = Analysis(
    [str(project_dir / "main.py")],
    pathex=[str(project_dir)],
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
    name="PlayOnThere",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    exclude_binaries=True,
    icon=str(icon_ico) if icon_ico.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PlayOnThere",
)