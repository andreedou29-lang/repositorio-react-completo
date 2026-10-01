import os
import re

file_path = "src/App.tsx"

if not os.path.exists(file_path):
    print(f"[ERROR] No se encontró {file_path}")
    exit(1)

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Normalizar filtros duplicados en carpetas de semestres
patron_filtro = r'(\.filter\(\(c:\s*any\)\s*=>\s*\(typeof c === \'string\' \? c : c\.nombre \|\| c\.name \|\| \'\'\) !== \'Libros\'\))+'
code = re.sub(patron_filtro, ".filter((c: any) => (typeof c === 'string' ? c : c.nombre || c.name || '') !== 'Libros')", code)

# 2. Bloque de código JSX con sintaxis balanceada (paréntesis y llaves)
bloque_biblioteca_limpio = """{/* Biblioteca de Libros */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
        {(documentos || []).filter((doc: any) => doc.pdf_bucket === 'repository-books' || (doc.source_rel_path && doc.source_rel_path.toLowerCase().includes('libros')) || (doc.pdf_storage_path && doc.pdf_storage_path.toLowerCase().includes('libros'))).length === 0 ? (
          <p className="text-gray-500 py-4">No hay libros registrados aún en la biblioteca.</p>
        ) : (
          (documentos || [])
            .filter((doc: any) => doc.pdf_bucket === 'repository-books' || (doc.source_rel_path && doc.source_rel_path.toLowerCase().includes('libros')) || (doc.pdf_storage_path && doc.pdf_storage_path.toLowerCase().includes('libros')))
            .map((libro: any) => (
              <div key={libro.id || libro.document_id} className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm bg-white dark:bg-gray-800 flex flex-col justify-between">
                <div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">PDF</span>
                  <h4 className="font-bold text-lg mt-2 text-gray-900 dark:text-white truncate" title={libro.title || libro.nombre}>
                    {libro.title || libro.nombre || 'Libro sin título'}
                  </h4>
                </div>
                <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-between items-center">
                  <span className="text-xs text-gray-400">
                    {libro.pdf_size_bytes || libro.size_bytes ? ((libro.pdf_size_bytes || libro.size_bytes) / 1024 / 1024).toFixed(1) + ' MB' : 'Documento'}
                  </span>
                  {libro.url && (
                    <a href={libro.url} target="_blank" rel="noreferrer" className="px-3 py-1.5 bg-slate-700 hover:bg-slate-800 text-white rounded-md text-xs font-medium transition-colors">
                      Ver / Descargar
                    </a>
                  )}
                </div>
              </div>
            ))
        )}
      </div>"""

# Reemplazar únicamente el fragmento desbalanceado
patrones_busqueda = [
    r'\{\/\* (Biblioteca|Catálogo|Sección)[\s\S]*?<\/div>\s*<\/div>',
    r'\{\/\* (Biblioteca|Catálogo|Sección)[\s\S]*?<\/div>',
    r'\(documentos \|\| \[\]\)\.filter[\s\S]*?<\/div>'
]

reemplazado = False
for patron in patrones_busqueda:
    if re.search(patron, code):
        code = re.sub(patron, bloque_biblioteca_limpio, code, count=1)
        reemplazado = True
        break

if not reemplazado and "Esta sección se configurará próximamente." in code:
    code = code.replace("Esta sección se configurará próximamente.", bloque_biblioteca_limpio)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("[ÉXITO] Archivo src/App.tsx corregido con sintaxis totalmente válida.")
