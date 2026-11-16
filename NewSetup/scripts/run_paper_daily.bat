@echo off
rem UGT-15 Phase 4: NewSetup daily paper-trading cycle (playbook 4.5).
rem Scheduled task: UGT15_NewSetupPaperDaily (daily 15:45 server-local, after
rem the 17:00 ET NY close; see C:\workspace\startup\README.md inventory).
rem One cycle: Layer1 scan -> Layer2 confirm -> Layer3 size -> paper fills ->
rem daily report -> funnel rows -> paper book persisted for the next cycle.
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs
echo ================================================================ >> logs\paper_daily.log
echo ===== %date% %time% UGT15_NewSetupPaperDaily cycle ===== >> logs\paper_daily.log
C:\Python314\python.exe main.py --once >> logs\paper_daily.log 2>&1
echo ===== exit %ERRORLEVEL% at %time% ===== >> logs\paper_daily.log
endlocal
