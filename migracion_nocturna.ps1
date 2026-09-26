$ErrorActionPreference = "Continue"
$proyecto = "C:\Users\USUARIO\OneDrive - Universidad Central del Ecuador\Escritorio\repositorio-react-completo\repositorio-react"
$log = "C:\Users\USUARIO\OneDrive - Universidad Central del Ecuador\Escritorio\Bobeda\migracion_nocturna.log"

Set-Location $proyecto
$env:PATH += ";C:\Users\USUARIO\AppData\Local\Pandoc"

"===== MIGRACION NOCTURNA $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') =====" | Out-File $log -Append -Encoding utf8

py -3 .\migrar_obsidian.py --todo 2>&1 | Tee-Object -FilePath $log -Append

"===== FIN $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') =====" | Out-File $log -Append -Encoding utf8
