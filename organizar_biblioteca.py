import os
import glob
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL", "").rstrip("/")
key = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY", "")

print("=== [1/2] Actualizando registros en la Base de Datos ===")

if url and key:
    endpoint = f"{url}/rest/v1/documents?file_path=ilike.*Libros*"
    headers = {
        "Authorization": f"Bearer {key}",
        "apiKey": key,
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    payload = json.dumps({"bucket": "repository-books"}).encode("utf-8")
    req = Request(endpoint, data=payload, headers=headers, method="PATCH")
    try:
        with urlopen(req) as resp:
            print("[OK] Registros de 'Libros' etiquetados correctamente en Supabase.")
    except Exception as e:
        print(f"[!] Aviso DB: {e}")
else:
    print("[!] No se encontraron credenciales completas de Supabase en .env, pasando al frontend...")

print("\n=== [2/2] Actualizando componentes en ./src ===")

archivos = glob.glob("src/**/*.jsx", recursive=True) + glob.glob("src/**/*.tsx", recursive=True) + glob.glob("src/**/*.js", recursive=True)

target_file = None
for f in archivos:
    try:
        with open(f, "r", encoding="utf-8") as file:
            content = file.read()
            if "Esta sección se configurará próximamente" in content or "Biblioteca de Libros" in content:
                target_file = f
                break
    except Exception:
        continue

if not target_file:
    print("[!] No se encontró el componente de Biblioteca directamente en ./src.")
    print("Archivos analizados:")
    for f in archivos:
        print(f" - {f}")
else:
    print(f"[OK] Componente encontrado: {target_file}")
    
    with open(target_file, "r", encoding="utf-8") as f:
        code = f.read()

    modificado = False

    # 1. Filtro para ocultar la carpeta 'Libros' en 'Archivo Personal'
    if ".filter(" in code and "Libros" not in code:
        # Reemplazamos mapeos de carpetas para omitir 'Libros'
        code = code.replace(".map(carpeta", ".filter(c => (typeof c === 'string' ? c : c.nombre || c.name || '') !== 'Libros').map(carpeta")
        code = code.replace(".map((carpeta", ".filter(c => (typeof c === 'string' ? c : c.nombre || c.name || '') !== 'Libros').map((carpeta")
        modificado = True
        print("[OK] Se añadió el filtro para excluir 'Libros' de Carpeta / Semestres en Archivo Personal.")

    # 2. Reemplazo del mensaje estático en 'Biblioteca de Libros'
    if "Esta sección se configurará próximamente." in code:
        remplazo_libros = """{/* Catálogo de Biblioteca de Libros */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
        {(documentos || []).filter(doc => doc.bucket === 'repository-books' || (doc.file_path && doc.file_path.includes('Libros'))).length === 0 ? (
          <p className="text-gray-500 py-4">No hay libros registrados aún en la biblioteca.</p>
        ) : (
          (documentos || [])
            .filter(doc => doc.bucket === 'repository-books' || (doc.file_path && doc.file_path.includes('Libros')))
            .map(libro => (
              <div key={libro.id || libro.document_id} className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm bg-white dark:bg-gray-800 flex flex-col justify-between">
                <div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">PDF</span>
                  <h4 className="font-bold text-lg mt-2 text-gray-900 dark:text-white truncate" title={libro.title || libro.nombre}>{libro.title || libro.nombre || 'Libro sin título'}</h4>
                </div>
                <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-between items-center">
                  <span className="text-xs text-gray-400">{libro.size ? (libro.size / 1024 / 1024).toFixed(1) + ' MB' : 'Documento'}</span>
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
        code = code.replace("Esta sección se configurará próximamente.", remplazo_libros)
        modificado = True
        print("[OK] Se reemplazó el texto estático por el renderizado de la Biblioteca de Libros.")

    if modificado:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(code)
        print("[ÉXITO] Archivo React actualizado correctamente.")
    else:
        print("[!] No se requirieron cambios adicionales en el código.")

print("\n=== Proceso completado ===")
