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

print("\n=== VERIFICACION SUPABASE ===")

folders = sb.table("folders").select("id").limit(1000).execute().data or []
documents = sb.table("documents").select("id").limit(1000).execute().data or []

print(f"folders   : {len(folders)}")
print(f"documents : {len(documents)}")

for bucket in ["repository-files", "repository-pdfs", "repository-images"]:
    items = sb.storage.from_(bucket).list(
        "",
        {
            "limit": 1000,
            "offset": 0,
            "sortBy": {"column": "name", "order": "asc"},
        },
    ) or []

    print(f"{bucket}: {len(items)}")

print("\n=== FIN ===")
