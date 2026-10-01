import os
import json
from urllib.request import Request, urlopen
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL", "").rstrip("/")
key = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY", "")

if not url or not key:
    print("[ERROR] No se encontraron las claves en el archivo .env")
    exit(1)

# Endpoint con filtro codificado correctamente para PostgREST
endpoint = f"{url}/rest/v1/documents?file_path=ilike.*Libros*"

headers = {
    "Authorization": f"Bearer {key}",
    "apiKey": key,
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

payload = json.dumps({"bucket": "repository-books"}).encode("utf-8")
req = Request(endpoint, data=payload, headers=headers, method="PATCH")

try:
    with urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"[ÉXITO] Se actualizaron {len(res)} registros de 'Libros' en la base de datos.")
except Exception as e:
    print(f"[!] Ocurrió un error al actualizar por REST: {e}")
