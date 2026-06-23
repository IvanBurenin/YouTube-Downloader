; Inno Setup script — создаёт установщик YouTubeDownloaderSetup.exe
; Скачайте Inno Setup: https://jrsoftware.org/isinfo.php
; Сборка: откройте этот файл в Inno Setup Compiler и нажмите "Compile"
; (предварительно соберите dist\YouTubeDownloader.exe через PyInstaller)

#define MyAppName "YouTube Downloader"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MyTools"
#define MyAppExeName "YouTubeDownloader.exe"

[Setup]
AppId={{B1E0B9B2-1234-4F6A-9A11-YTDOWNLOADER}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=YouTubeDownloaderSetup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "dist\YouTubeDownloader.exe"; DestDir: "{app}"; Flags: ignoreversion
; ffmpeg.exe обязателен — положите его рядом со скриптом перед сборкой
Source: "ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать значок на рабочем столе"; GroupDescription: "Дополнительно:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent
