from __future__ import annotations

import hashlib
import mimetypes
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from dotenv import load_dotenv

BUCKET = "repository-books"


def cargar_config() -> tuple[str, str, Path]:
    load_dotenv()

    required = ("SUPABASE_URL", "SUPABASE_SECRET_KEY")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Faltan variables en .env: " + ", ".join(missing))

    books_root = Path(r"C:\Users\USUARIO\Desktop\Andre\Libros")

    if not books_root.is_dir():
        raise RuntimeError(f"No existe la carpeta de libros: {books_root}")

    return os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"], books_root


def sha256_archivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def subir_a_supabase(url: str, key: str, bucket: str, path_local: Path, path_remoto: str) -> bool:
    # Codificamos la ruta para manejar espacios, acentos y caracteres especiales en URLs
    path_remoto_encoded = quote(path_remoto, safe="/")
    endpoint = f"{url.rstrip('/')}/storage/v1/object/{bucket}/{path_remoto_encoded}"

    content_type, _ = mimetypes.guess_type(path_local)
    if not content_type:
        content_type = "application/octet-stream"

    headers = {
        "Authorization": f"Bearer {key}",
        "apiKey": key,
        "x-upsert": "true",
        "Content-Type": content_type,
    }

    with path_local.open("rb") as f:
        data = f.read()

    req = Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urlopen(req) as resp:
            return resp.status in (200, 201)
    except HTTPError as e:
        print(f"[ERROR {e.code}] No se pudo subir {path_remoto}: {e.read().decode('utf-8')}")
        return False


def main():
    try:
        url, secret_key, books_root = cargar_config()
    except Exception as e:
        print(f"[ERROR CONFIG] {e}")
        sys.exit(1)

    print(f"Iniciando escaneo en: {books_root}")

    archivos = [p for p in books_root.rglob("*") if p.is_file()]
    if not archivos:
        print("No se encontraron archivos para subir.")
        return

    print(f"Se encontraron {len(archivos)} archivo(s). Subiendo a '{BUCKET}'...\n")

    exitosos = 0
    for archivo in archivos:
        rel_path = archivo.relative_to(books_root).as_posix()
        print(f"Subiendo: {rel_path} ... ", end="", flush=True)

        if subir_a_supabase(url, secret_key, BUCKET, archivo, rel_path):
            print("[OK]")
            exitosos += 1

    print(f"\nProceso finalizado: {exitosos}/{len(archivos)} archivos subidos correctamente.")


if __name__ == "__main__":
    main()
