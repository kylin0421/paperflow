#define MyAppName "Paper Flow"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Paper Flow Contributors"
#define MyAppExeName "PaperFlow.exe"

[Setup]
AppId={{6E37FC21-6DD2-46E1-AD72-82BE3D0D48BF}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Paper Flow
DefaultGroupName={#MyAppName}
OutputDir=..\dist\installer
OutputBaseFilename=PaperFlow-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\branding\PaperFlow.ico
AppMutex=Local\PaperFlowDesktopApp

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Files]
Source: "..\dist\PaperFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut / 创建桌面快捷方式"; GroupDescription: "Shortcuts / 快捷方式"

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Preparing the Windows WebView runtime... / 正在准备 Windows WebView 运行时…"; Flags: waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Paper Flow / 启动 Paper Flow"; Flags: nowait postinstall skipifsilent
