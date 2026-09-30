from pathlib import Path
from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv(Path(".env"))

s = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SECRET_KEY"]
)

vault = Path(os.environ["OBSIDIAN_VAULT_PATH"])

folders = s.table("folders").select(
    "id,name,parent_id"
).execute().data

documents = s.table("documents").select(
    "folder_id"
).execute().data

by_id = {f["id"]: f for f in folders}

document_count = {}
for d in documents:
    document_count[d["folder_id"]] = document_count.get(d["folder_id"], 0) + 1


def get_path(folder_id):
    parts = []
    current = by_id[folder_id]

    while current:
        parts.append(current["name"])
        current = by_id.get(current["parent_id"])

    return Path(*reversed(parts))


print()
print("==============================================")
print("CARPETAS SUPABASE CON 0 DOCUMENTOS")
print("==============================================")

empty = []

for folder in folders:
    if document_count.get(folder["id"], 0) == 0:

        relative_path = get_path(folder["id"])
        local_path = vault / relative_path

        if local_path.exists():
            files = [x for x in local_path.rglob("*") if x.is_file()]
        else:
            files = []

        empty.append((relative_path, files))

print()
print("TOTAL CARPETAS VACIAS EN SUPABASE:", len(empty))
print()

for i, (relative_path, files) in enumerate(
    sorted(empty, key=lambda x: str(x[0]).lower()), 1
):

    print(f"{i}. {relative_path}")
    print(f"   ARCHIVOS EN OBSIDIAN: {len(files)}")

    for file in files:
        print(f"      - {file.relative_to(vault)}")

    print()
