@echo off
rem LangSmith Studio 一键启动（cmd 双击或直接输 studio 即可）
rem %~dp0 = 本文件所在目录（项目根），无论从哪里运行都会先回到项目根
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
"E:\software\OfficeWorkLife\Anaconda\envs\studio_env\Scripts\langgraph.exe" dev
