; Inno Setup script for Argos. Wraps the PyInstaller one-dir output (dist/Argos) into a
; Windows installer. Build with scripts/build_release.ps1, or:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\argos.iss

#define AppName "Argos"
#define AppVersion "0.1.0"
#define AppPublisher "Santiago Quiroz"
#define AppExe "Argos.exe"

[Setup]
AppId={{5B8F1E2A-4C3D-4A9E-9F1B-ARGOS0000001}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=ArgosSetup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; The whole PyInstaller one-dir output.
Source: "..\dist\Argos\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
; The app is frozen-aware: at runtime it writes its DB/crops/.env to %LOCALAPPDATA%\Argos
; (the running user's), regardless of WorkingDir — so no per-user dirs are created at install time.
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
Name: "firewall"; Description: "Allow Argos through the Windows Firewall (LAN access)"; GroupDescription: "Network:"

[Run]
; Optional: open the LAN port through the firewall so other devices can reach the UI.
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""Argos"" dir=in action=allow protocol=TCP localport=8080"; Flags: runhidden; Tasks: firewall
Filename: "{app}\{#AppExe}"; Description: "Launch Argos now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""Argos"""; Flags: runhidden; RunOnceId: "DelArgosFirewall"
