@echo off
setlocal
set "task_error=0"

cd /d "%~dp0"

if errorlevel 1 exit /b 1

echo ================================================== >> "%~dp0sincronizacion.log"
echo INICIO: %date% %time% >> "%~dp0sincronizacion.log"
echo ================================================== >> "%~dp0sincronizacion.log"

echo [ACADEMICO] >> "%~dp0sincronizacion.log"
py -3 "%~dp0migrar_obsidian.py" --todo >> "%~dp0sincronizacion.log" 2>&1

if errorlevel 1 (
    set "task_error=1"
    echo [ERROR] Fallo la sincronizacion academica. >> "%~dp0sincronizacion.log"
) else (
    echo [OK] Sincronizacion academica terminada. >> "%~dp0sincronizacion.log"
)

echo. >> "%~dp0sincronizacion.log"
echo [LIBROS] >> "%~dp0sincronizacion.log"
py -3 "%~dp0sincronizar_biblioteca.py" >> "%~dp0sincronizacion.log" 2>&1

if errorlevel 1 (
    set "task_error=1"
    echo [ERROR] Fallo la sincronizacion de libros. >> "%~dp0sincronizacion.log"
) else (
    echo [OK] Sincronizacion de libros terminada. >> "%~dp0sincronizacion.log"
)

echo FIN: %date% %time% >> "%~dp0sincronizacion.log"
echo. >> "%~dp0sincronizacion.log"

endlocal & exit /b %task_error%
