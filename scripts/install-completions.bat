@echo off
REM Install shell completions for TASAK (Windows version)

echo TASAK Shell Completions Installer (Windows)
echo ============================================
echo.
echo Windows Command Prompt and PowerShell don't support
echo tab completion for Python scripts in the same way as
echo Unix shells (bash/zsh/fish).
echo.
echo However, you can use TASAK with these alternatives:
echo.
echo 1. PowerShell with PSReadLine:
echo    - TASAK commands will appear in your command history
echo    - Use arrow keys to navigate previous commands
echo.
echo 2. Windows Terminal:
echo    - Provides better command history and search
echo    - Press Ctrl+R to search command history
echo.
echo 3. Use Git Bash or WSL:
echo    - Run the Unix version: ./install-completions.sh
echo    - Full tab completion support
echo.
echo 4. Create aliases in PowerShell profile:
echo    - Add to $PROFILE:
echo      function tk { tasak @args }
echo    - Now use: tk [tab] for shorter typing
echo.
pause
