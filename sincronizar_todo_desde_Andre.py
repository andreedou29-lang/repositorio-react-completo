from pathlib import Path
from dotenv import load_dotenv
import os
from supabase import create_client

from migrar_obsidian import Migrador, cargar_config

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

config = cargar_config()

client = create_client(
    config.url,
    config.key
)

migrador = Migrador(client, config)

# La carpeta raíz real de Supabase es "Andre".
root_rows = (
    client
    .table("folders")
    .select("id,name,parent_id")
    .eq("name", config.vault.name)
    .is_("parent_id", "null")
    .limit(2)
    .execute()
    .data
    or []
)

if len(root_rows) != 1:
    raise RuntimeError(
        f"No se encontró exactamente una carpeta raíz '{config.vault.name}'. "
        f"Encontradas: {len(root_rows)}"
    )

root_id = root_rows[0]["id"]

# IMPORTANTE:
# "." y "" representan la carpeta raíz Andre.
migrador.folder_map = {
    ".": root_id,
    "": root_id,
}

archivos = list(migrador.archivos())

print()
print("==============================================")
print("MIGRACION COMPLETA OBSIDIAN -> SUPABASE")
print("==============================================")
print(f"Raiz: {config.vault}")
print(f"Archivos .md/.pdf encontrados: {len(archivos)}")
print()

ok = 0
errores = 0
omitidos = 0

for numero, archivo in enumerate(archivos, 1):

    print()
    print(f"[{numero}/{len(archivos)}] {archivo.relative_to(config.vault)}")

    try:

        if archivo.suffix.lower() == ".md":
            resultado = migrador.sincronizar_nota(archivo)

        elif archivo.suffix.lower() == ".pdf":
            resultado = migrador.sincronizar_pdf(archivo)

        else:
            omitidos += 1
            print("[OMITIDO] Tipo no soportado")
            continue

        if resultado:
            ok += 1
        else:
            omitidos += 1

    except Exception as error:
        errores += 1
        print(f"[ERROR] {error}")

print()
print("==============================================")
print("MIGRACION TERMINADA")
print("==============================================")
print(f"Encontrados : {len(archivos)}")
print(f"Procesados  : {ok}")
print(f"Omitidos    : {omitidos}")
print(f"Errores     : {errores}")
print()
print("Obsidian NO fue modificado.")
