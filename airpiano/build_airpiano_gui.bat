@echo off
setlocal

echo [BUILD] Running PyInstaller...
pyinstaller --onefile --noconsole --name AirPiano airpiano_gui.py

echo.
echo [DONE] Check dist\airPiano_gui.exe (또는 AirPiano.exe 이름일 수 있습니다)
echo 배포 시에는 dist\*.exe 를 상위 폴더로 옮기고, chord.CSV / progression.CSV 와 같은 폴더에 두세요.
pause