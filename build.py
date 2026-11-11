"""
打包脚本：生成单文件 exe（含 customtkinter 资源）
用法: .venv\Scripts\python.exe build.py
产物: dist\画师串管理器.exe
"""
import os
import sys
import shutil
from pathlib import Path
import customtkinter

try:
    import tkinterdnd2
    DND_PATH = os.path.join(tkinterdnd2.__path__[0], "tkdnd")
    DND_DATA = f",\n        ('{DND_PATH.replace(chr(92), chr(92)*4)}', 'tkinterdnd2/tkdnd')"
except ImportError:
    DND_DATA = ""

CTK_PATH = customtkinter.__path__[0]
PROJECT = "artist_manager"
OUT_NAME = "画师串管理器"

SPEC = f"""# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['{PROJECT}/main.py'],
    pathex=['{PROJECT}'],
    binaries=[],
    datas=[
        ('{CTK_PATH.replace(chr(92), chr(92)*4)}', 'customtkinter'),
        {DND_DATA.strip().lstrip(',')}
    ],
    hiddenimports=[
        'darkdetect',
        'tkinterdnd2',
        'PIL', 'PIL.Image', 'PIL.ImageOps', 'PIL.ImageTk',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'IPython', 'jupyter', 'notebook',
        'pytest', 'unittest', 'tkinter.test',
    ],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='{OUT_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='{OUT_NAME}',
)
"""


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    spec_path = os.path.join(root, "build.spec")
    dist_dir = os.path.join(root, "dist")
    build_dir = os.path.join(root, "build")

    # 清理旧产物
    for d in (dist_dir, build_dir):
        if os.path.isdir(d):
            shutil.rmtree(d)
    if os.path.isfile(spec_path):
        os.remove(spec_path)

    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(SPEC)

    print(f"spec → {spec_path}")
    print(f"ctk  → {CTK_PATH}")
    print("打包中…")

    os.chdir(root)
    rc = os.system(
        f'{sys.executable} -m PyInstaller '
        f'--noconfirm --clean "{spec_path}"'
    )

    if rc == 0 and os.path.isdir(dist_dir):
        exe = os.path.join(dist_dir, OUT_NAME, f"{OUT_NAME}.exe")
        size_mb = os.path.getsize(exe) / (1024 * 1024) if os.path.isfile(exe) else 0
        folder_size = sum(
            f.stat().st_size for f in Path(dist_dir, OUT_NAME).rglob("*") if f.is_file()
        ) / (1024 * 1024)
        print(f"\n打包成功")
        print(f"  目录: {os.path.join(dist_dir, OUT_NAME)}")
        print(f"  总大小: {folder_size:.1f} MB")
        print(f"  exe:    {size_mb:.1f} MB")
    else:
        print(f"\n打包失败 (rc={rc})")
        sys.exit(1)


if __name__ == "__main__":
    main()
