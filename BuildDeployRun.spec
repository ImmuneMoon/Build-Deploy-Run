# BuildDeployRun.spec
# Build with:  python -m PyInstaller BuildDeployRun.spec --clean --noconfirm

block_cipher = None

a = Analysis(
    ['install_config/install_workers/GUI/main.py'],
    pathex=['.'],
    binaries=[],
    # Everything the installer copies into a user project must be bundled here;
    # install_utils.get_bdr_source_dir() reads them from sys._MEIPASS when frozen.
    datas=[
        ('assets/icon.ico', 'assets'),
        ('assets/icon.png', 'assets'),
        ('deploy_fusion_runner.py', '.'),
        ('requirements.txt', '.'),
        ('workers/*.py', 'workers'),
    ],
    hiddenimports=[
        'plyer',
        'plyer.platforms.win.notification',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['numpy', 'scipy', 'pandas', 'matplotlib'],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BuildDeployRun',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # windowed: no command prompt behind the GUI
    icon='assets/icon.ico',
    version='version.txt',
)
