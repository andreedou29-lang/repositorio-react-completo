"""Instala archivos locales y guarda un respaldo; no publica ni sube datos."""
from datetime import datetime
from pathlib import Path
import shutil
import sys

BASE = Path(__file__).resolve().parent
DEFAULT_PROJECT = Path(r"C:\Users\USUARIO\Desktop\repositorio-react-completo\repositorio-react")
FILES = [
    "src/App.tsx", "src/types.ts", "src/styles.css",
    "src/lib/repository.ts", "src/lib/normalizeNote.ts",
    "src/components/Reader.tsx", "convertir_nota.py", "normalizar_latex.py",
    "migrar_obsidian.py", "lote_obsidian.py",
    "supabase/functions/serve-pdf/index.ts",
]


def main():
    project = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PROJECT
    if not (project / "package.json").is_file() or not (project / "src").is_dir():
        raise RuntimeError(f"No se encuentra el proyecto React en: {project}")
    if not (project / "migrar_obsidian.py").is_file():
        raise RuntimeError("Falta migrar_obsidian.py en el proyecto. Este paquete actualiza la integracion ya configurada.")
    files = FILES + [name for name in ("callouts.lua", "estilos.tex") if not (project / name).exists()]
    for name in files:
        if not (BASE / name).is_file():
            raise RuntimeError(f"Falta {name} en el paquete. Extrae el ZIP completo antes de ejecutar.")
    backup = project / "respaldos" / ("lector-pdf-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    backup.mkdir(parents=True)
    # Respaldar todos los archivos existentes antes de reemplazar el primero.
    for name in files:
        target = project / name
        if target.exists():
            old = backup / name
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, old)
    for name in files:
        target = project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BASE / name, target)
        print(f"[OK] {name}")
    print(f"\nParche instalado en: {project}\nRespaldo: {backup}")
    print("Ahora ejecuta npm.cmd run build en el proyecto.")
    print("Para regenerar y subir todas las notas: py -3 .\\migrar_obsidian.py --todo")
    print("La funcion serve-pdf debe estar desplegada en Supabase para abrir los PDF.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        raise SystemExit(1)
