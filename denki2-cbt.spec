# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 第二種電気工事士 CBT Windows EXE."""

import os
from pathlib import Path

# プロジェクトルート（このファイルの場所）
ROOT = Path(SPECPATH)
SERVER = ROOT / "server"

a = Analysis(
    [str(SERVER / "launcher.py")],
    pathex=[str(SERVER)],  # models.py を import 可能にする
    binaries=[],
    datas=[
        (str(SERVER / "templates"), "templates"),
        (str(SERVER / "static"), "static"),
        (str(SERVER / "instance" / "app.db"), "instance"),
    ],
    hiddenimports=[
        "flask",
        "flask_sqlalchemy",
        "sqlalchemy",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.sqlite.pysqlite",
        "sqlalchemy.orm",
        "models",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "gunicorn",
        "pdfplumber",
        "pymupdf",
        "fitz",
        "pytest",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="denki2-cbt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # コンソールウィンドウを表示（起動メッセージ用）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="denki2-cbt",
)
