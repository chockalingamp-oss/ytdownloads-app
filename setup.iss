[Setup]
AppName=YTDownloads
AppVersion=1.0
DefaultDirName={autopf}\YTDownloads
DefaultGroupName=YTDownloads
OutputDir=C:\YTDownloads\InstallerOutput
OutputBaseFilename=YTDownloads_Setup
Compression=lzma
SolidCompression=yes

[Files]
; This packages your standalone executable into the installer
Source: "C:\YTDownloads\dist\YTDownloads.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Creates shortcuts in the Start Menu and on your Desktop
Name: "{group}\YTDownloads"; Filename: "{app}\YTDownloads.exe"
Name: "{commondesktop}\YTDownloads"; Filename: "{app}\YTDownloads.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked