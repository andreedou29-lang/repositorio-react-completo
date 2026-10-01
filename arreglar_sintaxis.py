import re

file_path = "src/App.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Corregir paréntesis desbalanceados (documentos || []))) -> (documentos || [])
code = re.sub(r'\(documentos\s*\|\|\s*\[\]\)\)+', '(documentos || [])', code)

# 2. Expresión de filtrado correcta para la vista de libros usando las columnas reales de Supabase
filtro_libros = "(documentos || []).filter((doc: any) => doc.pdf_bucket === 'repository-books' || (doc.source_rel_path && doc.source_rel_path.toLowerCase().includes('libros')) || (doc.pdf_storage_path && doc.pdf_storage_path.toLowerCase().includes('libros')))"

# 3. Aplicar el filtro de libros en la comprobación de longitud y en el renderizado
code = re.sub(r'\{\(documentos\s*\|\|\s*\[\]\)\.length', f'{{{filtro_libros}.length', code)
code = re.sub(r'\(documentos\s*\|\|\s*\[\]\)\.map', f'{filtro_libros}.map', code)

# 4. Eliminar filtros duplicados en las carpetas de semestres si los hubiera
patron_carpetas = ".filter((c: any) => (typeof c === 'string' ? c : c.nombre || c.name || '') !== 'Libros')"
while patron_carpetas + patron_carpetas in code:
    code = code.replace(patron_carpetas + patron_carpetas, patron_carpetas)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("[ÉXITO] Sintaxis de src/App.tsx corregida correctamente.")
