@echo off
REM Record the exact environment EATCalc numbers were produced with.
REM Run from the repo root after any install/upgrade:  scripts\freeze_env.bat
call conda activate totalseg
if not exist env mkdir env
TotalSegmentator --version > env\totalsegmentator_version.txt
python -m pip freeze > env\totalseg_env_lock.txt
call conda list --explicit > env\totalseg_conda_explicit.txt
echo Wrote env\totalsegmentator_version.txt, env\totalseg_env_lock.txt, env\totalseg_conda_explicit.txt
type env\totalsegmentator_version.txt
