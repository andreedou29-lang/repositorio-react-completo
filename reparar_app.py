import os

file_path = "src/App.tsx"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Filtro tapno maikkat ti 'Libros' idiay 'Archivo Personal' (Semestres)
    if "Libros" in code:
        code = code.replace(
            "carpetas.map(", 
            "carpetas.filter((c: any) => (typeof c === 'string' ? c : c.nombre || c.name || '') !== 'Libros').map("
        )
        code = code.replace(
            "folders.map(", 
            "folders.filter((c: any) => (typeof c === 'string' ? c : c.nombre || c.name || '') !== 'Libros').map("
        )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)

    print("[OK] Na-update ti App.tsx. Maikkat ti Libros idiay Archivo Personal.")
except Exception as e:
    print(f"[ERROR] Saan a na-update ti archivo: {e}")
