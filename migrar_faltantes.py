import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LISTA = BASE_DIR / "archivos_faltantes_migracion.txt"
MIGRADOR = BASE_DIR / "migrar_obsidian.py"

# Estos dos MD fueron corregidos y ahora existen como PDF.
IGNORAR = {
    "Teorema de Morera.md"
}

with open(LISTA, "r", encoding="utf-8") as f:
    archivos = [
        Path(line.strip())
        for line in f
        if line.strip()
    ]

print("=" * 60)
print("MIGRACION DE ARCHIVOS FALTANTES")
print("=" * 60)

# Eliminar los dos MD de Morera
archivos = [
    archivo
    for archivo in archivos
    if archivo.name not in IGNORAR
]

print(f"Archivos a procesar: {len(archivos)}")
print()

errores = []
procesados = 0

for i, archivo in enumerate(archivos, 1):

    print(f"[{i}/{len(archivos)}] {archivo}")

    if not archivo.exists():
        print("   ERROR: archivo no encontrado")
        errores.append(str(archivo))
        continue

    resultado = subprocess.run(
        [
            "python",
            str(MIGRADOR),
            "--nota",
            str(archivo)
        ],
        cwd=str(BASE_DIR),
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if resultado.returncode == 0:
        print("   OK")
        procesados += 1
    else:
        print("   ERROR")
        errores.append(str(archivo))

print()
print("=" * 60)
print("RESULTADO")
print("=" * 60)
print(f"Procesados correctamente: {procesados}")
print(f"Errores: {len(errores)}")

if errores:
    print()
    print("ARCHIVOS CON ERROR:")
    for i, archivo in enumerate(errores, 1):
        print(f"{i:02d}. {archivo}")

    with open(
        BASE_DIR / "errores_migracion_faltantes.txt",
        "w",
        encoding="utf-8"
    ) as f:
        for archivo in errores:
            f.write(archivo + "\n")
else:
    print()
    print("TODOS LOS ARCHIVOS FUERON PROCESADOS CORRECTAMENTE.")