# PyInstaller spec — собирает приложение в один .exe (onefile, без консоли)
# Сборка: pyinstaller build.spec

block_cipher = None

from PyInstaller.utils.hooks import collect_data_files

# Собираем данные certifi, как и было
datas_certifi = collect_data_files('certifi')

# Добавляем к ним вашу иконку, чтобы она была доступна окну изнутри .exe
datas_certifi.append(('resources/app.ico', 'resources'))

# --- ВАЖНО: Принудительно упаковываем файлы самого плагина ---
try:
    import yt_dlp_youtube_oauth2
    import os
    plugin_dir = os.path.dirname(yt_dlp_youtube_oauth2.__file__)
    # Копируем папку плагина во внутреннюю директорию yt_dlp_plugins пакета
    datas_certifi.append((plugin_dir, 'yt_dlp_plugins/youtube_oauth2'))
except ImportError:
    pass
# -----------------------------------------------------------

a = Analysis(
    ['main.py'],
    pathex=['.'],
    # ffmpeg остается в binaries для корректной распаковки
    binaries=[('ffmpeg.exe', '.')],
    datas=datas_certifi,
    # Добавляем плагины yt_dlp в hiddenimports, чтобы они не потерялись при сборке
    hiddenimports=[
        'yt_dlp', 
        'yt_dlp_youtube_oauth2', 
        'yt_dlp_oauth'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
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
    name='YouTubeDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    # Иконка для самого .exe файла в проводнике Windows
    icon='resources/app.ico',
)