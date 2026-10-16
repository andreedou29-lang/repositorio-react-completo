@echo off
cd /d "C:\Users\USUARIO\Desktop\repositorio-react-completo\repositorio-react"

echo ==========================================
echo   SINCRONIZACION OBSIDIAN - SUPABASE
echo ==========================================
echo.
echo Inicio: %date% %time%
echo.

py -3 .\migrar_obsidian.py --todo

echo.
echo Fin: %date% %time%
echo ==========================================
echo   SINCRONIZACION TERMINADA
echo ==========================================