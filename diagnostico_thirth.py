from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv(".env")
c = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])

f = c.table("folders").select("id,name,parent_id").execute().data or []
d = c.table("documents").select("id,original_name,folder_id,storage_path").execute().data or []

byid = {x["id"]: x for x in f}

def getpath(i):
    p = []
    while i is not None:
        x = byid[i]
        p.append(x["name"])
        i = x["parent_id"]
    return "/".join(reversed(p))

folderpaths = {x["id"]: getpath(x["id"]) for x in f}

print("=== CARPETAS THIRTH ===")
thirth = {
    x["id"]: folderpaths[x["id"]]
    for x in f
    if folderpaths[x["id"]].startswith("THIRTH")
}

for fid, path in thirth.items():
    destino = path[7:] if path.startswith("THIRTH/") else ""
    existe = any(folderpaths[y["id"]] == destino for y in f)
    print(path, "=>", destino, "| DESTINO:", "OK" if existe else "FALTA")

print()
print("=== DOCUMENTOS EN THIRTH ===")
docs_thirth = [
    x for x in d
    if x["folder_id"] in thirth
]
print("TOTAL:", len(docs_thirth))

print()
print("=== POSIBLES COLISIONES ===")
colisiones = 0

for x in docs_thirth:
    origen = folderpaths[x["folder_id"]]
    destino = origen[7:]
    
    existe = any(
        y["id"] != x["id"]
        and y["original_name"] == x["original_name"]
        and folderpaths.get(y["folder_id"]) == destino
        for y in d
    )
    
    if existe:
        print(x["original_name"], "| destino:", destino)
        colisiones += 1

print("TOTAL COLISIONES:", colisiones)
print()
print("FIN - NO SE MODIFICO NADA")
