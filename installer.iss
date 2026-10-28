#define AppVersion "1.0.3"

[Setup]
AppId={{E4F3D632-BD11-4662-A8CC-959EE9DC16EB}
AppName=Mini-Island
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\MiniIsland
DefaultGroupName=Mini-Island
PrivilegesRequired=lowest
OutputDir=installer_out
OutputBaseFilename=MiniIsland-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=yes

[Files]
Source: "dist\MiniIsland\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Mini-Island"; Filename: "{app}\MiniIsland.exe"

[Run]
; без skipifsilent: после тихого обновления остров сразу запускается снова
Filename: "{app}\MiniIsland.exe"; Description: "Запустить Mini-Island"; Flags: nowait postinstall

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var R: Integer;
begin
  // закрываем запущенный остров, иначе файлы заняты
  Exec('taskkill', '/F /IM MiniIsland.exe', '', SW_HIDE, ewWaitUntilTerminated, R);
  Result := '';
end;
