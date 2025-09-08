@echo off
set HOST_NAME=com.sakib.ytdownloader
set MANIFEST_PATH=C:\yt_downloader\server\native_host_manifest.json

rem Add registry key for Chrome
REG ADD "HKEY_CURRENT_USER\Software\Google\Chrome\NativeMessagingHosts\%HOST_NAME%" /ve /t REG_SZ /d "%MANIFEST_PATH%" /f

if %errorlevel% == 0 (
  echo Native messaging host for Chrome has been installed successfully.
) else (
  echo Failed to install native messaging host for Chrome.
)

pause

