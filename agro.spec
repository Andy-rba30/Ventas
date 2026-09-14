# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller: `pyinstaller agro.spec --noconfirm` -> dist/AgroNegocio/ (onedir, sin consola).

Incluye los assets de customtkinter (temas e iconos), tkcalendar y la carpeta assets/ del
proyecto. babel.numbers lo carga tkcalendar en tiempo de ejecución y PyInstaller no lo detecta solo.
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("customtkinter") + collect_data_files("tkcalendar") + [("assets", "assets")]
hiddenimports = ["babel.numbers"] + collect_submodules("tkcalendar")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["pandas", "matplotlib", "numpy", "scipy", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AgroNegocio",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icono.ico",
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="AgroNegocio")
