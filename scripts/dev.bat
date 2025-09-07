@echo off
REM Development helper script for TASAK (Windows version)

setlocal enabledelayedexpansion

if "%1"=="" goto :help
if "%1"=="help" goto :help
if "%1"=="setup" goto :setup
if "%1"=="test" goto :test
if "%1"=="lint" goto :lint
if "%1"=="clean" goto :clean
if "%1"=="install" goto :install

echo Unknown command: %1
goto :help

:help
echo TASAK Development Helper (Windows)
echo.
echo Usage: dev.bat [COMMAND]
echo.
echo Commands:
echo     setup       Set up development environment
echo     test        Run tests
echo     lint        Run linters and formatters
echo     clean       Clean up build artifacts and caches
echo     install     Install in editable mode
echo     help        Show this help message
echo.
echo Examples:
echo     dev.bat setup      # First-time setup
echo     dev.bat test       # Run all tests
echo     dev.bat lint       # Check code quality
goto :eof

:setup
echo Setting up TASAK development environment...
echo.

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install development dependencies
echo Installing dependencies...
pip install -e "."
pip install pytest pytest-cov pre-commit ruff ipython

REM Install pre-commit hooks
echo Installing pre-commit hooks...
pre-commit install

REM Create default config directories
echo Creating config directories...
if not exist "%USERPROFILE%\.tasak\plugins\python" mkdir "%USERPROFILE%\.tasak\plugins\python"
if not exist ".tasak\plugins\python" mkdir ".tasak\plugins\python"

echo.
echo Development environment ready!
echo Activate with: .venv\Scripts\activate.bat
goto :eof

:test
echo Running tests...
pytest -v
goto :eof

:lint
echo Running code quality checks...

REM Run ruff
echo Running ruff...
ruff check . --fix
ruff format .

REM Run pre-commit
echo Running pre-commit hooks...
pre-commit run --all-files

echo Code quality checks complete!
goto :eof

:clean
echo Cleaning build artifacts...

REM Remove Python artifacts
for /r %%i in (__pycache__) do if exist "%%i" rmdir /s /q "%%i"
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul
del /s /q *.pyd 2>nul
del /s /q .coverage 2>nul

REM Remove build artifacts
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist ".pytest_cache" rmdir /s /q ".pytest_cache"
if exist ".ruff_cache" rmdir /s /q ".ruff_cache"
if exist "htmlcov" rmdir /s /q "htmlcov"
for /d %%i in (*.egg-info) do rmdir /s /q "%%i"

echo Cleaned!
goto :eof

:install
echo Installing TASAK in editable mode...
pip install -e "."
echo TASAK installed!
goto :eof

endlocal
