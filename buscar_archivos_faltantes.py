from pathlib import Path
from dotenv import load_dotenv
import os
import re
import unicodedata
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
    "title,original_name,folder_id,extension"
).eq("extension", "pdf").execute().data

by_id = {f["id"]: f for f in folders}


def folder_path(folder_id):
    parts = []
    current = by_id.get(folder_id)

    while current:
        parts.append(current["name"])
        current = by_id.get(current["parent_id"])

    return "/".join(reversed(parts))


def norm(text):
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"\.pdf$", "", text, flags=re.I)
    text = re.sub(r"\.md$", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    return text


supabase_files = set()

for d in documents:
    folder = folder_path(d["folder_id"])
    name = d["original_name"] or d["title"]
    supabase_files.add((norm(folder), norm(name)))

missing = []

for file in vault.rglob("*"):

    if not file.is_file():
        continue

    ext = file.suffix.lower()

    if ext not in [".md", ".pdf"]:
        continue

    relative = file.relative_to(vault)
    parent = relative.parent

    if str(parent) == ".":
        folder = ""
    else:
        folder = str(parent).replace("\\", "/")

    if ext == ".md":
        expected_name = file.stem
    else:
        expected_name = file.name

    key = (norm(folder), norm(expected_name))

    if key not in supabase_files:
        missing.append((str(relative), ext))

print()
print("==============================================")
print("ARCHIVOS DE OBSIDIAN SIN PDF EN SUPABASE")
print("==============================================")
print()
print("TOTAL:", len(missing))
print()

for i, (path, ext) in enumerate(missing, 1):
    print(f"{i}. [{ext}] {path}")
