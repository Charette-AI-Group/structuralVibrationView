; Installer for Structural Vibration View. Built with Inno Setup 6:
;
;     ISCC.exe installer\structuralVibrationView.iss
;
; It expects dist\StructuralVibrationView\ to exist - run tools\buildExe.py
; first. The version is passed in by tools\buildInstaller.py so that it can
; never disagree with appConfig; the default below is only what a bare ISCC
; run would use.
;
; Per-user by design. This app draws pictures of vibrating beams; it needs
; nothing machine-wide, and asking for administrator rights to install a
; teaching tool is how a small program becomes a thing IT has to approve.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "Structural Vibration View"
#define ShortName "StructuralVibrationView"
#define Publisher "Charette AI Group, LLC"
#define AppUrl "https://github.com/Charette-AI-Group/structuralVibrationView"
#define ExeName "StructuralVibrationView.exe"
#define BundleDir "..\dist\StructuralVibrationView"

[Setup]
; Fixed for the life of the application: this is what lets an upgrade replace
; an install rather than sit beside it, and what the uninstaller is found by.
AppId={{2B9E7C41-6D18-4A52-8F3B-5C0A91D7E4A6}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
AppPublisher={#Publisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}
AppUpdatesURL={#AppUrl}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
SetupIconFile=..\src\structuralVibrationView\resources\structuralVibrationView.ico
UninstallDisplayIcon={app}\{#ExeName}
UninstallDisplayName={#AppName}
OutputDir=..\dist
OutputBaseFilename=structuralVibrationViewSetup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Per-user, so there is no UAC prompt and no Program Files. The application
; writes only to APPDATA, so nothing here needs more than the user has.
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Shown on the first page, so the licence is read before anything is written.
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; The bundle only. Deliberately not the settings under APPDATA: an uninstall
; that silently discards somebody's structure, material and window position is
; a surprise, and a reinstall is the commonest reason to uninstall.
Type: filesandordirs; Name: "{app}\_internal"

[Code]
{ A running copy holds its own files open, so replacing them mid-upgrade fails
  with a message about a file in use that says nothing about why. Ask first
  instead, in words that name the application. The main window's title is
  exactly "Structural Vibration View" (appConfig.windowTitle).

  SuppressibleMsgBox, not MsgBox: a plain MsgBox still appears under
  /SUPPRESSMSGBOXES and would hang a silent install. Silently, the answer is
  No - abort cleanly rather than fail halfway on a file in use. }
function InitializeSetup(): Boolean;
var
  WindowHandle: HWND;
begin
  Result := True;
  WindowHandle := FindWindowByWindowName('{#AppName}');
  if WindowHandle <> 0 then
    Result := SuppressibleMsgBox(
      '{#AppName} appears to be running.' + #13#10#13#10 +
      'Close it before continuing, or setup cannot replace its files.' + #13#10#13#10 +
      'Continue anyway?',
      mbConfirmation, MB_YESNO, IDNO) = IDYES;
end;
