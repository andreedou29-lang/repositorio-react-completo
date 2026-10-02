@echo off
setlocal

cd /d "C:\Users\USUARIO\Desktop\repositorio-react-completo\repositorio-react"

echo ================================================== >> sincronizacion.log
echo INICIO: %date% %time% >> sincronizacion.log
echo ================================================== >> sincronizacion.log

echo [ACADEMICO] >> sincronizacion.log
py -3 ".\migrar_obsidian.py" --todo >> sincronizacion.log 2>&1

if errorlevel 1 (
    echo [ERROR] Fallo la sincronizacion academica. >> sincronizacion.log
) else (
    echo [OK] Sincronizacion academica terminada. >> sincronizacion.log
)

echo. >> sincronizacion.log
echo [LIBROS] >> sincronizacion.log
py -3 ".\migrar_libros.py" >> sincronizacion.log 2>&1

if errorlevel 1 (
    echo [ERROR] Fallo la sincronizacion de libros. >> sincronizacion.log
) else (
    echo [OK] Sincronizacion de libros terminada. >> sincronizacion.log
)

echo FIN: %date% %time% >> sincronizacion.log
echo. >> sincronizacion.log

endlocal
