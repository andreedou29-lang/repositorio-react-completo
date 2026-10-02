import os
import re
import hashlib
from dotenv import load_dotenv
from supabase import create_client, Client

dir_actual = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(dir_actual, ".env"))

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SECRET_KEY") or 
    os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY") or
    os.getenv("VITE_SUPABASE_ANON_KEY") or 
    os.getenv("SUPABASE_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] Credenciales no encontradas.")
    exit(1)

SUPABASE_URL = SUPABASE_URL.replace("\n", "").replace("\r", "").strip()
SUPABASE_KEY = SUPABASE_KEY.replace("\n", "").replace("\r", "").strip()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

ORIGEN_LIBROS = r"C:\Users\USUARIO\Desktop\Andre\Libros"
BUCKET_NAME = "repository-books"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

def calcular_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def sanitizar_storage_path(relative_path):
    path_clean = relative_path.replace("\\", "/")
    parts = path_clean.split("/")
    clean_parts = []
    for part in parts:
        clean_name = re.sub(r"[^a-zA-Z0-9\s_.-]", "", part)
        clean_parts.append(clean_name.strip())
    return "/".join(clean_parts)

def sincronizar():
    print("\n=== INICIANDO SINCRONIZACIÓN DE BIBLIOTECA ===")
    
    try:
        res_db = supabase.table("books").select("id, relative_path, source_sha256").execute()
        libros_db = {doc["relative_path"]: doc for doc in res_db.data} if res_db.data else {}
    except Exception as e:
        print(f"[ADVERTENCIA] Consulta inicial a DB: {e}")
        libros_db = {}

    archivos_procesados = 0
    for root, _, files in os.walk(ORIGEN_LIBROS):
        for file in files:
            if not file.lower().endswith(".pdf"):
                continue

            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, ORIGEN_LIBROS)
            file_size = os.path.getsize(full_path)

            if file_size > MAX_FILE_SIZE:
                print(f"[OMITIDO - >50MB] {rel_path} ({file_size / (1024*1024):.2f} MB)")
                continue

            file_hash = calcular_sha256(full_path)
            clean_storage_key = sanitizar_storage_path(rel_path)

            if rel_path in libros_db and libros_db[rel_path].get("source_sha256") == file_hash:
                print(f"[AL DÍA] {rel_path}")
                archivos_procesados += 1
                continue

            print(f"[SUBIENDO] {rel_path} ({file_size / (1024*1024):.2f} MB)...")
            
            with open(full_path, "rb") as f:
                try:
                    supabase.storage.from_(BUCKET_NAME).upload(
                        path=clean_storage_key,
                        file=f,
                        file_options={"x-upsert": "true", "content-type": "application/pdf"}
                    )
                except Exception as e:
                    print(f"  [ERROR STORAGE] {e}")
                    continue

            storage_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{clean_storage_key}"

            data_book = {
                "title": os.path.splitext(file)[0],
                "original_name": file,
                "relative_path": rel_path,
                "storage_path": clean_storage_key,
                "size_bytes": file_size,
                "source_sha256": file_hash,
                "url": storage_url
            }

            try:
                if rel_path in libros_db:
                    supabase.table("books").update(data_book).eq("relative_path", rel_path).execute()
                    print(f"  [DB ACTUALIZADA]")
                else:
                    supabase.table("books").insert(data_book).execute()
                    print(f"  [DB INSERTADA]")
            except Exception as e:
                # Reintentar omitiendo el campo 'url' si la columna aún no existe
                if "url" in str(e):
                    data_book.pop("url", None)
                    try:
                        if rel_path in libros_db:
                            supabase.table("books").update(data_book).eq("relative_path", rel_path).execute()
                            print(f"  [DB ACTUALIZADA (sin columna url)]")
                        else:
                            supabase.table("books").insert(data_book).execute()
                            print(f"  [DB INSERTADA (sin columna url)]")
                    except Exception as e_inner:
                        print(f"  [ERROR DB FINAL] {e_inner}")
                else:
                    print(f"  [ERROR DB] {e}")

            archivos_procesados += 1

    print(f"\n=== SINCRONIZACIÓN FINALIZADA ({archivos_procesados} libros procesados) ===")

if __name__ == "__main__":
    sincronizar()
