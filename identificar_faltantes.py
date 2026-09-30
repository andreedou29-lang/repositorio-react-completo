from pathlib import Path
from dotenv import load_dotenv
import os
import re
import unicodedata
from supabase import create_client

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

VAULT = Path(os.environ["OBSIDIAN_VAULT_PATH"]).resolve()

sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SECRET_KEY"]
)

print("\n==============================================")
print("IDENTIFICANDO ARCHIVOS QUE FALTAN")
print("==============================================")
print(f"Raiz: {VAULT}")
print()


def norm(text):
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        c for c in text
        if unicodedata.category(c) != "Mn"
    )
    text = text.casefold().strip()
    text = re.sub(r"\s+", " ", text)
    return text


# -------------------------------------------------
# 1. Cargar carpetas de Supabase
# -------------------------------------------------

folders = (
    sb
    .table("folders")
    .select("id,name,parent_id")
    .limit(1000)
    .execute()
    .data
    or []
)

folder_by_id = {f["id"]: f for f in folders}


def folder_path(folder_id):
    partes = []

    while folder_id is not None:
        folder = folder_by_id.get(folder_id)

        if folder is None:
            raise RuntimeError(
                f"No se encuentra folder_id={folder_id}"
            )

        partes.append(folder["name"])
        folder_id = folder["parent_id"]

    return "/".join(reversed(partes))


# -------------------------------------------------
# 2. Cargar documentos actuales
# -------------------------------------------------

documents = (
    sb
    .table("documents")
    .select("id,title,original_name,folder_id,extension")
    .limit(1000)
    .execute()
    .data
    or []
)

supabase_docs = set()

for doc in documents:

    folder = folder_path(doc["folder_id"])

    nombre = doc["original_name"] or doc["title"]

    # Guardamos ruta completa normalizada
    supabase_docs.add(
        (
            norm(folder),
            norm(nombre)
        )
    )


# -------------------------------------------------
# 3. Recorrer TODOS los .md y .pdf de Obsidian
# -------------------------------------------------

locales = []

for archivo in VAULT.rglob("*"):

    if not archivo.is_file():
        continue

    if archivo.name.startswith("."):
        continue

    extension = archivo.suffix.lower()

    if extension not in {".md", ".pdf"}:
        continue

    relativa = archivo.relative_to(VAULT)

    carpeta = relativa.parent

    if str(carpeta) == ".":
        carpeta_relativa = VAULT.name
    else:
        carpeta_relativa = (
            VAULT.name + "/" +
            str(carpeta).replace("\\", "/")
        )

    # Los MD deben existir como PDF en Supabase
    if extension == ".md":
        nombre_esperado = archivo.stem + ".pdf"
    else:
        nombre_esperado = archivo.name

    locales.append(
        (
            archivo,
            carpeta_relativa,
            nombre_esperado
        )
    )


# -------------------------------------------------
# 4. Identificar faltantes
# -------------------------------------------------

faltantes = []

for archivo, carpeta, nombre in locales:

    clave = (
        norm(carpeta),
        norm(nombre)
    )

    if clave not in supabase_docs:
        faltantes.append(
            (
                archivo,
                carpeta,
                nombre
            )
        )


# -------------------------------------------------
# 5. Mostrar resultado
# -------------------------------------------------

print(f"Archivos locales .md/.pdf : {len(locales)}")
print(f"Documentos en Supabase    : {len(documents)}")
print(f"FALTANTES                 : {len(faltantes)}")
print()

print("==============================================")
print("ARCHIVOS FALTANTES")
print("==============================================")
print()

for i, (archivo, carpeta, nombre) in enumerate(faltantes, 1):

    extension = archivo.suffix.lower()

    print(
        f"{i:02d}. [{extension}] "
        f"{archivo.relative_to(VAULT)}"
    )


# -------------------------------------------------
# 6. Guardar lista para corregirlos después
# -------------------------------------------------

salida = BASE / "archivos_faltantes_migracion.txt"

with salida.open("w", encoding="utf-8") as f:

    for archivo, carpeta, nombre in faltantes:
        f.write(str(archivo) + "\n")

print()
print("==============================================")
print(f"Lista guardada en:")
print(salida)
print("==============================================")
