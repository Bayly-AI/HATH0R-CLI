@echo off
REM Hath0r CLI Standalone Executable (Windows Entry)
set SCRIPT_DIR=%~dp0
python -m hath0r_cli.cli %*
