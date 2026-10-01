import os
import re

file_path = "src/App.tsx"

if not os.path.exists(file_path):
    for root, dirs, files in os.walk("src"):
        for f in files:
            if f in ["App.tsx", "App.jsx"]:
                file_path = os.path.join(root, f)
                break

print(f"Procesando archivo: {file_path}")

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Limpiar filtros duplicados o mal formateados que provocaban la pantalla en blanco
code = re.sub(r'(\.filter\([^)]*Libros[^)]*\))+', '', code)

# 2. Excluir la carpeta 'Libros' de la lista de carpetas en 'Archivo Personal'
if "carpetas.map" in code:
    code = code.replace("carpetas.map", "carpetas.filter((c: any) => (typeof c === 'string' ? c : c.nombre || c.name || '') !== 'Libros').map")

if "folders.map" in code:
    code = code.replace("folders.map", "folders.filter((c: any) => (typeof c === 'string' ? c : c.nombre || c.name || '') !== 'Libros').map")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("[ÉXITO] src/App.tsx corregido exitosamente.")
