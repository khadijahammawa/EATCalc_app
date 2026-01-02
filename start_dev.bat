@echo off

echo Starting EATCalc development servers...

REM Start backend
start cmd /k uvicorn backend.server:app --reload --port 8000

REM Start frontend
start cmd /k npm run dev -- --host 127.0.0.1 --port 8080
