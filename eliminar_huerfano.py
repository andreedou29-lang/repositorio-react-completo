import os

file_path = "src/App.tsx"

if not os.path.exists(file_path):
    print("No se encontró src/App.tsx")
    exit(1)

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

nuevas_lineas = []
eliminadas = 0

for i, line in enumerate(lines):
    # Eliminar líneas que solo contienen ')}' o '})' que quedaron colgadas en la sección
    if line.strip() in [")}", "})", "}"] and i > 120:
        print(f"Eliminando cierre huérfano en línea {i + 1}: {line.strip()}")
        eliminadas += 1
        continue
    nuevas_lineas.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(nuevas_lineas)

print(f"[ÉXITO] Se corregió el archivo. Líneas huérfanas eliminadas: {eliminadas}")
