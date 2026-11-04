[Setup]
AppName=YTDownloads
AppVersion=1.1
AppPublisher=YTDownloads Team
DefaultDirName={autopf}\YTDownloads
DefaultGroupName=YTDownloads
AllowNoIcons=yes
OutputDir=C:\YTDownloads\InstallerOutput
OutputBaseFilename=YTDownloads_Setup_v1.1
SetupIconFile=C:\YTDownloads\app_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\YTDownloads\dist\YTDownloads.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\YTDownloads\app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\YTDownloads"; Filename: "{app}\YTDownloads.exe"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\YTDownloads"; Filename: "{app}\YTDownloads.exe"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\YTDownloads.exe"; Description: "{cm:LaunchProgram,YTDownloads}"; Flags: nowait postinstall skipifsilent