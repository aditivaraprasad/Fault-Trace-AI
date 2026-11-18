@echo off
setlocal
set "GIT_EXE=C:\Users\Aditi V Gowda\AppData\Local\GitHubDesktop\app-3.5.9\resources\app\git\cmd\git.exe"

echo =======================================================
echo  Pushing FAULTTRACE AI to GitHub
echo  Repository: https://github.com/Kavya1696/FaultTrace-AI
echo =======================================================
echo.

"%GIT_EXE%" remote set-url origin https://github.com/Kavya1696/FaultTrace-AI.git
"%GIT_EXE%" push -u origin main

echo.
if errorlevel 1 (
    echo [!] Push encountered an authentication or permission error.
    echo If prompted, enter your GitHub Personal Access Token (PAT) as password.
) else (
    echo [OK] Successfully pushed to https://github.com/Kavya1696/FaultTrace-AI
)

pause
