from pathlib import Path
import subprocess
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

VAULT = Path(r"C:\Users\USUARIO\OneDrive\Andre\THIRTH")
SCRIPT = Path(__file__).parent / "migrar_obsidian.py"


class ObsidianHandler(FileSystemEventHandler):

    def __init__(self):
        self.last_run = 0

    def changed(self, path):
        now = time.time()

        if now - self.last_run < 3:
            return

        self.last_run = now
        p = Path(path)

        if p.name.startswith(".") or ".obsidian" in p.parts:
            return

        if p.suffix.lower() not in {".md", ".pdf"}:
            return

        print(f"[CAMBIO] {p}")

        try:
            subprocess.run(
                ["py", "-3", str(SCRIPT), "--nota", str(p)],
                cwd=str(SCRIPT.parent),
                check=False
            )
        except Exception as e:
            print(f"[ERROR] {e}")

    def on_created(self, event):
        if not event.is_directory:
            self.changed(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.changed(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.changed(event.dest_path)


observer = Observer()
observer.schedule(
    ObsidianHandler(),
    str(VAULT),
    recursive=True
)

observer.start()

print("========================================")
print(" MONITOR DE OBSIDIAN ACTIVO")
print("========================================")
print(f"Vault: {VAULT}")
print("Esperando cambios...")
print("Presiona Ctrl+C para detener.")
print("========================================")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()

observer.join()