@echo off
set CLAUDE_SONNET_MODEL=claude-haiku-4-5
set CLAUDE_HAIKU_MODEL=claude-haiku-4-5
set CLAUDE_OPUS_MODEL=claude-haiku-4-5
set CLAUDE_DEFAULT_MODEL=claude-haiku-4-5
cd /d "D:\Smartgrow Projects\BharatBuild_AI\backend"
"D:\Smartgrow Projects\BharatBuild_AI\backend\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
