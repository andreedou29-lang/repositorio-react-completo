import re

file_path = "src/App.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Eliminar duplicados en los filtros de carpetas
patron_filtro = r'(\.filter\(\(c:\s*any\)\s*=>\s*\(typeof c === \'string\' \? c : c\.nombre \|\| c\.name \|\| \'\'\) !== \'Libros\'\))+'
code = re.sub(patron_filtro, ".filter((c: any) => (typeof c === 'string' ? c : c.nombre || c.name || '') !== 'Libros')", code)

# 2. Definición limpia del catálogo para 'Biblioteca de Libros'
bloque_biblioteca = """{/* Sección Biblioteca de Libros */}
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
                  <h4 className="font-bold text-lg mt-2 text-gray-900 dark:text-white truncate" title={libro.title || libro.nombre}>{libro.title || libro.nombre || 'Libro sin título'}</h4>
                </div>
                <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-between items-center">
                  <span className="text-xs text-gray-400">{libro.pdf_size_bytes || libro.size_bytes ? ((libro.pdf_size_bytes || libro.size_bytes) / 1024 / 1024).toFixed(1) + ' MB' : 'Documento'}</span>
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

# 3. Reemplazar la sección corrupta
if "Sección Biblioteca de Libros" in code or "Catálogo de Biblioteca de Libros" in code:
    code = re.sub(r'\{\/\* (Sección|Catálogo) Biblioteca de Libros \*\/\}[\s\S]*?<\/div>', bloque_biblioteca, code)
else:
    code = code.replace("Esta sección se configurará próximamente.", bloque_biblioteca)

# 4. Limpiar paréntesis desbalanceados residuales
code = re.sub(r'\n\s*\)\)\s*\n', '\n', code)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("[ÉXITO] Sintaxis de src/App.tsx corregida.")
