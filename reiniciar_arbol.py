from pathlib import Path
from dotenv import load_dotenv
import os
from supabase import create_client

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SECRET_KEY"]
)

# Leer todas las carpetas
folders = sb.table("folders").select("id,name,parent_id").execute().data or []

# Borrar primero las mas profundas
parents = {f["id"]: f["parent_id"] for f in folders}

def depth(folder_id):
    d = 0
    current = folder_id
    while current is not None:
        d += 1
        current = parents.get(current)
    return d

folders = sorted(folders, key=lambda f: depth(f["id"]), reverse=True)

print("\nEliminando arbol anterior...")

for folder in folders:
    sb.table("folders").delete().eq("id", folder["id"]).execute()
    print(f"[ELIMINADA] {folder['name']}")

print(f"\nCarpetas eliminadas: {len(folders)}")

# Corregir la raiz
env_file = BASE / ".env"
lines = env_file.read_text(encoding="utf-8").splitlines()

new_lines = []
encontrada = False

for line in lines:
    if line.startswith("OBSIDIAN_VAULT_PATH="):
        new_lines.append(
            "OBSIDIAN_VAULT_PATH=C:\\Users\\USUARIO\\OneDrive - Universidad Central del Ecuador\\Andre"
        )
        encontrada = True
    else:
        new_lines.append(line)

if not encontrada:
    new_lines.append(
        "OBSIDIAN_VAULT_PATH=C:\\Users\\USUARIO\\OneDrive - Universidad Central del Ecuador\\Andre"
    )

env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

print("\nRaiz corregida:")
print("C:\\Users\\USUARIO\\OneDrive - Universidad Central del Ecuador\\Andre")

print("\nSupabase queda sin carpetas y listo para reconstruir.")
