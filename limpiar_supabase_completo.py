from pathlib import Path
from dotenv import load_dotenv
import os
from supabase import create_client

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SECRET_KEY"]

supabase = create_client(url, key)

print("\n========================================")
print("LIMPIEZA TOTAL DE DATOS DE MIGRACION")
print("========================================\n")

confirmacion = input(
    "Esto eliminara TODOS los documentos, carpetas y archivos "
    "de los buckets repository-files, repository-pdfs y repository-images.\n"
    "Escribe BORRAR TODO para continuar: "
)

if confirmacion != "BORRAR TODO":
    print("\nOperacion cancelada.")
    raise SystemExit(0)


def listar_archivos(bucket, path=""):
    resultados = []
    offset = 0

    while True:
        items = supabase.storage.from_(bucket).list(
            path,
            {
                "limit": 1000,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )

        if not items:
            break

        for item in items:
            name = item.get("name", "")
            if not name:
                continue

            # Los objetos tienen metadata; las carpetas virtuales normalmente no.
            if item.get("id") is not None:
                full_path = f"{path}/{name}" if path else name
                resultados.append(full_path)
            else:
                subpath = f"{path}/{name}" if path else name
                resultados.extend(listar_archivos(bucket, subpath))

        if len(items) < 1000:
            break

        offset += 1000

    return resultados


def limpiar_bucket(bucket):
    print(f"\n[STORAGE] {bucket}")

    archivos = listar_archivos(bucket)

    if not archivos:
        print("  Ya estaba vacio.")
        return 0

    print(f"  Archivos encontrados: {len(archivos)}")

    eliminados = 0

    for i in range(0, len(archivos), 100):
        lote = archivos[i:i + 100]
        supabase.storage.from_(bucket).remove(lote)
        eliminados += len(lote)
        print(f"  Eliminados: {eliminados}/{len(archivos)}")

    return eliminados


# 1. Eliminar documentos
print("\n[DB] Eliminando documents...")
response = (
    supabase
    .table("documents")
    .delete()
    .neq("id", "00000000-0000-0000-0000-000000000000")
    .execute()
)
print("[OK] documents limpiado.")


# 2. Eliminar carpetas
print("\n[DB] Eliminando folders...")
response = (
    supabase
    .table("folders")
    .delete()
    .neq("id", "00000000-0000-0000-0000-000000000000")
    .execute()
)
print("[OK] folders limpiado.")


# 3. Storage
total_storage = 0

for bucket in (
    "repository-files",
    "repository-pdfs",
    "repository-images",
):
    total_storage += limpiar_bucket(bucket)


print("\n========================================")
print("LIMPIEZA TERMINADA")
print("========================================")
print("documents : 0")
print("folders   : 0")
print(f"storage   : {total_storage} archivos eliminados")
print("\nSupabase queda listo para la nueva migracion.")
