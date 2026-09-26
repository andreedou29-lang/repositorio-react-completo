from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv(".env")
c = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])

folders = c.table("folders").select("id,name,parent_id").execute().data or []
docs = c.table("documents").select("id,original_name,folder_id,storage_path").execute().data or []

byid = {x["id"]: x for x in folders}

def path(i):
    p = []
    while i is not None:
        p.append(byid[i]["name"])
        i = byid[i]["parent_id"]
    return "/".join(reversed(p))

paths = {x["id"]: path(x["id"]) for x in folders}

# Solo carpetas dentro de THIRTH
thirth_folders = {
    x["id"]: paths[x["id"]]
    for x in folders
    if paths[x["id"]].startswith("THIRTH/")
}

# Crear mapa de carpetas destino
destino_ids = {}

for fid, oldpath in thirth_folders.items():
    destino = oldpath[len("THIRTH/"):]
    
    # Buscar carpeta destino exacta
    encontrada = next(
        (x for x in folders if paths[x["id"]] == destino),
        None
    )
    
    if encontrada:
        destino_ids[fid] = encontrada["id"]

# Detectar carpetas faltantes
faltantes = [
    (fid, oldpath, oldpath[len("THIRTH/"):])
    for fid, oldpath in thirth_folders.items()
    if fid not in destino_ids
]

print("CARPETAS DENTRO DE THIRTH:", len(thirth_folders))
print("DESTINOS YA EXISTENTES:", len(destino_ids))
print("DESTINOS FALTANTES:", len(faltantes))

print()
print("=== SE CREARAN ===")
for _, oldpath, destino in faltantes:
    print(oldpath, "=>", destino)

print()
print("=== DOCUMENTOS A MOVER ===")

docs_thirth = [
    x for x in docs
    if x["folder_id"] in thirth_folders
]

print("TOTAL:", len(docs_thirth))

# Crear carpetas destino de forma jerárquica
created = {}

def obtener_o_crear(ruta):
    if ruta == "":
        return None

    partes = ruta.split("/")
    padre = None
    acumulado = ""

    for nombre in partes:
        acumulado = nombre if not acumulado else acumulado + "/" + nombre

        existente = next(
            (
                x for x in folders
                if x["name"] == nombre and x["parent_id"] == padre
            ),
            None
        )

        if existente:
            padre = existente["id"]
            continue

        nuevo = {
            "id": __import__("uuid").uuid4().__str__(),
            "name": nombre,
            "parent_id": padre
        }

        c.table("folders").insert(nuevo).execute()
        folders.append(nuevo)
        byid[nuevo["id"]] = nuevo
        paths[nuevo["id"]] = acumulado

        print("CREADA:", acumulado)

        padre = nuevo["id"]

    return padre

# Crear todos los destinos
for _, oldpath in thirth_folders.items():
    destino = oldpath[len("THIRTH/"):]
    created[destino] = obtener_o_crear(destino)

print()
print("=== MOVIENDO DOCUMENTOS ===")

movidos = 0

for doc in docs_thirth:
    origen = paths[doc["folder_id"]]
    destino = origen[len("THIRTH/"):]
    nuevo_folder_id = created[destino]

    if not nuevo_folder_id:
        raise RuntimeError("No se pudo determinar destino: " + destino)

    c.table("documents").update({
        "folder_id": nuevo_folder_id
    }).eq("id", doc["id"]).execute()

    movidos += 1

print()
print("================================")
print("REPARACION TERMINADA")
print("DOCUMENTOS MOVIDOS:", movidos)
print("NO SE SUBIERON ARCHIVOS")
print("NO SE CAMBIARON STORAGE_PATH")
print("NO SE CAMBIARON IDs DE DOCUMENTOS")
print("================================")
