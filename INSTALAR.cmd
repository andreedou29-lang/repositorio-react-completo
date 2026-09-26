@echo off
py -3 "%~dp0instalar_parche.py"
if errorlevel 1 echo No se completo la instalacion. Revisa el error anterior.
pause
