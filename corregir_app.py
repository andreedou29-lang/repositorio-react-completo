file_path = "src/App.tsx"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Ajustamos los nombres de las columnas reales de la base de datos
    code = code.replace("doc.bucket", "doc.pdf_bucket")
    code = code.replace("doc.file_path", "doc.source_rel_path")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)

    print("[ÉXITO] src/App.tsx se actualizó correctamente.")
except Exception as e:
    print(f"[ERROR] No se pudo actualizar el archivo: {e}")
