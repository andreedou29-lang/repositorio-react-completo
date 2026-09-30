from pathlib import Path
from dotenv import load_dotenv
import os
from supabase import create_client

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

VAULT = Path(os.environ["OBSIDIAN_VAULT_PATH"]).resolve()

if not VAULT.is_dir():
    raise RuntimeError(f"No existe la raiz: {VAULT}")

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SECRET_KEY"]
)

# No queremos copiar la configuracion interna de Obsidian.
EXCLUDED_DIRS = {
    ".obsidian",
    ".trash",
}

def obtener_folder(name, parent_id):
    q = (
        supabase
        .table("folders")
        .select("id")
        .eq("name", name)
    )

    if parent_id is None:
        q = q.is_("parent_id", "null")
    else:
        q = q.eq("parent_id", parent_id)

    rows = q.limit(2).execute().data or []

    if len(rows) > 1:
        raise RuntimeError(
            f"Duplicado encontrado: {name} dentro de parent_id={parent_id}"
        )

    return rows[0]["id"] if rows else None


def crear_folder(name, parent_id):
    existente = obtener_folder(name, parent_id)

    if existente:
        return existente, False

    response = (
        supabase
        .table("folders")
        .insert({
            "name": name,
            "parent_id": parent_id
        })
        .execute()
    )

    if not response.data:
        raise RuntimeError(f"No se pudo crear la carpeta: {name}")

    return response.data[0]["id"], True


contador = 0

def recorrer_directorio(local_dir, parent_id, relative_path):
    global contador

    carpetas = sorted(
        [
            p for p in local_dir.iterdir()
            if p.is_dir()
            and not p.name.startswith(".")
            and p.name not in EXCLUDED_DIRS
        ],
        key=lambda p: p.name.casefold()
    )

    for carpeta in carpetas:
        carpeta_id, creada = crear_folder(carpeta.name, parent_id)

        ruta_relativa = (
            f"{relative_path}/{carpeta.name}"
            if relative_path
            else carpeta.name
        )

        if creada:
            contador += 1
            print(f"[CREADA] {ruta_relativa}")
        else:
            print(f"[EXISTE] {ruta_relativa}")

        recorrer_directorio(
            carpeta,
            carpeta_id,
            ruta_relativa
        )


print()
print("==============================================")
print("CONSTRUCCION DEL ARBOL OBSIDIAN -> SUPABASE")
print("==============================================")
print(f"Raiz local: {VAULT}")
print()

# La raiz Andre sera la raiz de Supabase.
root_id, root_created = crear_folder(VAULT.name, None)

if root_created:
    contador += 1
    print(f"[CREADA] {VAULT.name}")
else:
    print(f"[EXISTE] {VAULT.name}")

recorrer_directorio(
    VAULT,
    root_id,
    VAULT.name
)

print()
print("==============================================")
print("ARBOL TERMINADO")
print("==============================================")
print(f"Carpetas creadas: {contador}")
print()
print("NO se subieron archivos.")
print("NO se modifico Obsidian.")
