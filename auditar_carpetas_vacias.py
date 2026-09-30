from pathlib import Path
from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv(Path(".env"))

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SECRET_KEY"]
)

vault = Path(os.environ["OBSIDIAN_VAULT_PATH"])

folders = supabase.table("folders").select(
    "id,name,parent_id"
).execute().data

documents = supabase.table("documents").select(
    "folder_id"
).execute().data

folder_by_id = {f["id"]: f for f in folders}
document_count = {}

for d in documents:
    document_count[d["folder_id"]] = document_count.get(d["folder_id"], 0) + 1

def folder_path(folder_id):
    parts = []
    current = folder_by_id[folder_id]

    while current:
        parts.append(current["name"])
        parent_id = current["parent_id"]
        current = folder_by_id.get(parent_id)

    return "/".join(reversed(parts))

print("=== CARPETAS SIN DOCUMENTOS EN SUPABASE ===")

empty = []

for folder in folders:
    if document_count.get(folder["id"], 0) == 0:
        path = folder_path(folder["id"])
        local_path = vault / Path(path.replace("/", os.sep))

        if local_path.exists():
            files = [x for x in local_path.rglob("*") if x.is_file()]
            empty.append((path, files))

print("TOTAL:", len(empty))

for i, (path, files) in enumerate(sorted(empty), 1):
    print()
    print(f"{i}. {path}")
    print(f"   ARCHIVOS LOCALES: {len(files)}")

    for file in files:
        print(f"      - {file.relative_to(vault)}")
