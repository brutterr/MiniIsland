#define AppVersion "1.0.9"

[Setup]
AppId={{E4F3D632-BD11-4662-A8CC-959EE9DC16EB}
AppName=Mini-Island
AppVersion={#AppVersion}
AppVerName=Mini-Island {#AppVersion}
AppPublisher=brutterr
AppPublisherURL=https://github.com/brutterr/MiniIsland
VersionInfoVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\MiniIsland
DefaultGroupName=Mini-Island
PrivilegesRequired=lowest
OutputDir=installer_out
OutputBaseFilename=MiniIsland-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
; --- вид установщика: тёмный, в стиле острова ---
SetupIconFile=MiniIsland.ico
UninstallDisplayIcon={app}\MiniIsland.exe
WizardStyle=modern
WizardImageFile=installer_assets\wizard_100.bmp,installer_assets\wizard_150.bmp,installer_assets\wizard_200.bmp
WizardSmallImageFile=installer_assets\small_100.bmp,installer_assets\small_150.bmp,installer_assets\small_200.bmp
ShowLanguageDialog=no
DisableDirPage=yes
DisableReadyPage=yes
DisableProgramGroupPage=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Messages]
WelcomeLabel1=Mini-Island
WelcomeLabel2=Остров для рабочего стола: плеер, буфер обмена, загрузки, погода, таймер и быстрые инструменты в одном месте.%n%nУстановка займёт несколько секунд.
FinishedHeadingLabel=Готово!
FinishedLabel=Mini-Island установлен. Остров ждёт у верхнего края экрана.
FinishedLabelNoIcons=Mini-Island установлен. Остров ждёт у верхнего края экрана.
SetupAppTitle=Установка Mini-Island
SetupWindowTitle=Установка — Mini-Island

[Files]
Source: "dist\MiniIsland\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Mini-Island"; Filename: "{app}\MiniIsland.exe"

[Run]
; без skipifsilent: после тихого обновления остров сразу запускается снова
Filename: "{app}\MiniIsland.exe"; Description: "Запустить Mini-Island"; Flags: nowait postinstall

[Code]
const
  // цвета в формате $BBGGRR; те же, что у тёмной темы острова
  ColBg   = $161414;
  ColText = $F7F5F5;
  ColSub  = $A09A9A;

procedure InitializeWizard();
begin
  WizardForm.Color := ColBg;
  WizardForm.MainPanel.Color := ColBg;
  WizardForm.InnerPage.Color := ColBg;
  WizardForm.WelcomePage.Color := ColBg;
  WizardForm.FinishedPage.Color := ColBg;
  WizardForm.Bevel.Visible := False;
  WizardForm.Bevel1.Visible := False;

  WizardForm.WelcomeLabel1.Font.Color := ColText;
  WizardForm.WelcomeLabel2.Font.Color := ColSub;
  WizardForm.FinishedHeadingLabel.Font.Color := ColText;
  WizardForm.FinishedLabel.Font.Color := ColSub;
  WizardForm.PageNameLabel.Font.Color := ColText;
  WizardForm.PageDescriptionLabel.Font.Color := ColSub;
  WizardForm.StatusLabel.Font.Color := ColSub;
  WizardForm.FilenameLabel.Font.Color := ColSub;
  WizardForm.RunList.Color := ColBg;
  WizardForm.RunList.Font.Color := ColText;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  // страницы выбора папки и подтверждения отключены: с приветствия сразу идёт установка
  if CurPageID = wpWelcome then
    WizardForm.NextButton.Caption := 'Установить';
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var R: Integer;
begin
  // закрываем запущенный остров, иначе файлы заняты
  Exec('taskkill', '/F /IM MiniIsland.exe', '', SW_HIDE, ewWaitUntilTerminated, R);
  Result := '';
end;
