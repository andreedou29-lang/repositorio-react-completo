from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv(".env")
c = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])

folders = c.table("folders").select("id,name,parent_id").execute().data or []
docs = c.table("documents").select("id,original_name,folder_id").execute().data or []

byid = {x["id"]: x for x in folders}

def path(i):
    p = []
    while i is not None:
        p.append(byid[i]["name"])
        i = byid[i]["parent_id"]
    return "/".join(reversed(p))

paths = {x["id"]: path(x["id"]) for x in folders}

origen = next(x["id"] for x in folders if paths[x["id"]] == "ALGEBRA 2/Tareas")
destino = next(x["id"] for x in folders if paths[x["id"]] == "ECUACIONES DIFERENCIALES ORDINARIAS/Tareas")

n = 0

for doc in docs:
    if (
        doc["folder_id"] == origen
        and doc["original_name"] in [
            "TAREA CAPITULO 1 - EDO - ANDRE EDOU.md",
            "TAREA CAPITULO 2 - EDO - ANDRE EDOU.md"
        ]
    ):
        c.table("documents").update({
            "folder_id": destino
        }).eq("id", doc["id"]).execute()
        print("MOVIDO:", doc["original_name"])
        n += 1

print("TOTAL MOVIDOS:", n)
