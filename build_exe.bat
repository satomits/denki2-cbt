@echo off
chcp 65001 > nul
echo ============================================
echo  第二種電気工事士 CBT - Windows EXE ビルド
echo ============================================
echo.

echo [1/2] PyInstaller をインストール中...
pip install pyinstaller
if errorlevel 1 (
    echo エラー: PyInstaller のインストールに失敗しました。
    pause
    exit /b 1
)

echo.
echo [2/2] EXE をビルド中...
pyinstaller denki2-cbt.spec --noconfirm
if errorlevel 1 (
    echo エラー: ビルドに失敗しました。
    pause
    exit /b 1
)

echo.
echo ============================================
echo  ビルド完了！
echo  dist\denki2-cbt\denki2-cbt.exe をダブルクリックして起動してください。
echo ============================================
pause
