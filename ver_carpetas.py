from migrar_obsidian import cargar_config
from supabase import create_client

config = cargar_config()
client = create_client(config.url, config.key)

res = client.table("folders").select("id, name, parent_id").is_("parent_id", "null").execute()
print("--- CARPETAS EN LA RAÍZ (parent_id = NULL) ---")
for f in res.data:
    print(f"ID: {f['id']} | Nombre: {f['name']}")

andre = client.table("folders").select("id, name, parent_id").ilike("name", "%andr%").execute()
print("\n--- CARPETAS CON NOMBRE 'ANDRÉ' ---")
for f in andre.data:
    print(f"ID: {f['id']} | Nombre: {f['name']} | Parent: {f['parent_id']}")
