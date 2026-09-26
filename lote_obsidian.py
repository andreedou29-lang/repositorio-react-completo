"""Lotes reanudables. Estado local sin credenciales; servicios remotos inyectados."""
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
import csv
import hashlib
import io
import json
import os
import subprocess
import tempfile

from convertir_nota import programa, ruta_pdf
from normalizar_latex import preparar_boveda

BASE = Path(__file__).resolve().parent


class BovedaModificada(RuntimeError):
    pass


def sha_archivo(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def escribir_atomico(path, text):
    path = Path(path)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent,
                                         prefix=path.name + ".", delete=False) as f:
            temp = Path(f.name)
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        # En Windows hay que cerrar el archivo antes de eliminarlo.
        if temp is not None:
            temp.unlink(missing_ok=True)


@contextmanager
def bloqueo(output):
    # Bloqueo del sistema operativo: se libera incluso si termina el proceso.
    path = Path(output) / ".migracion.lock"
    with path.open("a+b") as f:
        f.seek(0, 2)
        if f.tell() == 0:
            f.write(b"0"); f.flush()
        f.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError("Ya hay otra migracion usando esta carpeta de salida. Espera o deten la otra ejecucion.") from error
        try:
            yield
        finally:
            f.seek(0)
            if os.name == "nt":
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def huella_lote(config, versiones=None):
    if versiones is None:
        versiones = {}
        for name in (config.exporter, "pandoc", "xelatex"):
            r = subprocess.run([programa(name), "--version"], capture_output=True, timeout=30, check=True)
            versiones[name] = r.stdout.decode("utf-8", errors="replace")
    codigo = {name: sha_archivo(BASE / name) for name in (
        "normalizar_latex.py", "convertir_nota.py", "migrar_obsidian.py", "lote_obsidian.py",
        "callouts.lua", "estilos.tex",
    )}
    # Huella base compartida por el lote: codigo, versiones de herramientas y
    # configuracion. NO incluye archivos de la boveda: cada archivo se compara
    # con huella_archivo() para saltar solo los que realmente no cambiaron.
    # Limitacion conocida: si un adjunto/imagen incrustado cambia sin tocar la
    # nota .md que lo referencia, esa nota no se detecta como desactualizada;
    # usa --forzar para esa nota en ese caso.
    data = {"codigo": codigo, "versiones": versiones, "proyecto": config.url,
            "vault": str(config.vault), "salida": str(config.output)}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def huella_archivo(huella_base, inventario, rel):
    archivo = inventario.get(rel)
    if archivo is None or archivo.get("sha256") is None:
        return None
    data = f"{huella_base}:{rel}:{archivo['sha256']}"
    return hashlib.sha256(data.encode()).hexdigest()


def validar_inventario(vault, inventario):
    for rel, expected in inventario.items():
        path = vault / rel
        try:
            stat = path.stat()
        except OSError as error:
            raise BovedaModificada(f"Un archivo cambio o desaparecio durante el lote: {rel}. Repite la ejecucion.") from error
        if (stat.st_size, stat.st_mtime_ns) != (expected["size"], expected["mtime_ns"]):
            raise BovedaModificada(f"Un archivo cambio durante el lote: {rel}. Repite la ejecucion cuando termines de editar.")


def ya_sincronizado(migrador, entry, huella, pdf):
    if not entry or entry.get("huella") != huella or not pdf.is_file():
        return False
    if sha_archivo(pdf) != entry.get("pdf_sha256"):
        return False
    expected = entry.get("documento", {})
    if not expected.get("id"):
        return False
    columns = "id,original_name,folder_id,storage_path,extension,pdf_bucket,pdf_storage_path,pdf_size_bytes"
    result = migrador.client.table("documents").select(columns).eq("id", expected["id"]).limit(2).execute()
    rows = result.data or []
    return len(rows) == 1 and all(rows[0].get(k) == expected.get(k) for k in columns.split(","))


def clasificar(error):
    text = str(error).lower()
    if isinstance(error, UnicodeError): return "codificacion"
    if isinstance(error, BovedaModificada): return "boveda_modificada"
    if any(s in text for s in ("adjunto", "imagen", "embedded", "incrustado")): return "adjunto"
    if "yaml" in text or "frontmatter" in text: return "metadatos"
    if "cierra el visor" in text or isinstance(error, PermissionError): return "archivo_bloqueado"
    if "registro:" in text or "xelatex" in text or "pandoc" in text: return "conversion"
    return "sincronizacion"


def guardar_informe(output, registros, total, terminado, general=""):
    counts = dict(Counter(r["estado"] for r in registros))
    report = {"actualizado": datetime.now(timezone.utc).isoformat(), "terminado": terminado,
              "total": total, "procesados": len(registros), "pendientes": total-len(registros),
              "resumen": counts, "error_general": general, "archivos": registros}
    escribir_atomico(output / "informe_migracion.json", json.dumps(report, indent=2, ensure_ascii=False))
    buffer = io.StringIO(newline="")
    fields = ["archivo", "estado", "categoria", "detalle", "registro", "document_id"]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for r in registros:
        safe = {}
        for key in fields:
            value = str(r.get(key, ""))
            safe[key] = "'" + value if value.startswith(("=", "+", "-", "@")) else value
        writer.writerow(safe)
    try:
        escribir_atomico(output / "informe_migracion.csv", "\ufeff" + buffer.getvalue())
    except PermissionError:
        print("[AVISO] Cierra el CSV para actualizarlo. El informe JSON si quedo guardado.", flush=True)


def ejecutar_lote(migrador, archivos, forzar=False, versiones=None):
    config = migrador.config
    output = config.output
    output.mkdir(parents=True, exist_ok=True)
    archivos = [Path(p).resolve() for p in archivos]

    if any(not p.is_relative_to(config.vault) for p in archivos):
        raise RuntimeError("Todos los archivos deben estar dentro de la boveda.")

    state_path = output / ".estado_migracion.json"
    registros = []

    with bloqueo(output):
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(state, dict) or not isinstance(state.get("archivos"), dict):
                raise ValueError("Estado invalido")
        except (FileNotFoundError, ValueError):
            state = {"version": 1, "archivos": {}}

        huella_base = huella_lote(config, versiones)
        candidatos = []

        # FILTRO INCREMENTAL:
        # solamente entran archivos nuevos o cuya huella cambio.
        for path in archivos:
            rel = path.relative_to(config.vault).as_posix()

            try:
                stat = path.stat()
                sha = sha_archivo(path)

                inventario_archivo = {
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "sha256": sha,
                }

                huella = huella_archivo(
                    huella_base,
                    {rel: inventario_archivo},
                    rel,
                )

                entry = state["archivos"].get(rel)
                pdf = ruta_pdf(config.vault, path, output)

                if (
                    not forzar
                    and entry
                    and entry.get("source_sha256") == sha
                    and (entry.get("documento") or entry.get("error"))
                ):
                    print(f"[SIN CAMBIOS] {rel}", flush=True)
                    continue

                candidatos.append((path, rel, huella))

            except OSError as error:
                print(f"[PENDIENTE] {rel}: {error}", flush=True)
                candidatos.append((path, rel, None))

        print(
            f"[INCREMENTAL] {len(candidatos)} archivos requieren sincronizacion.",
            flush=True,
        )

        if not candidatos:
            print("[INCREMENTAL] No hay archivos nuevos o modificados.", flush=True)
            guardar_informe(output, registros, 0, True)
            return 0

        original_converter = migrador.converter
        original_validator = migrador.validar_fuente

        terminado, general, code = False, "", 0

        try:
            guardar_informe(output, registros, len(candidatos), False)

            print(
                f"[LOTE] Procesando solamente {len(candidatos)} archivos.",
                flush=True,
            )

            for n, (path, rel, huella) in enumerate(candidatos, 1):
                pdf = ruta_pdf(config.vault, path, output)
                log = (
                    str(pdf.with_suffix(".conversion.log"))
                    if path.suffix.lower() == ".md"
                    else ""
                )

                record = {
                    "archivo": rel,
                    "estado": "",
                    "categoria": "",
                    "detalle": "",
                    "registro": log,
                    "document_id": "",
                }

                print(f"\n[{n}/{len(candidatos)}] {rel}", flush=True)

                try:
                    migrador.validar_fuente()

                    migrador.ultimo_documento = None

                    if path.suffix.lower() == ".pdf":
                        doc_id = migrador.sincronizar_pdf(path)
                    else:
                        doc_id = migrador.sincronizar_nota(path)

                    if doc_id:
                        columns = (
                            "id,original_name,folder_id,storage_path,extension,"
                            "pdf_bucket,pdf_storage_path,pdf_size_bytes"
                        ).split(",")

                        doc = {
                            k: migrador.ultimo_documento.get(k)
                            for k in columns
                        }

                        state["archivos"][rel] = {
                            "source_sha256": sha,
                            "source_size": path.stat().st_size,
                            "source_mtime_ns": path.stat().st_mtime_ns,
                            "documento": doc,
                            "pdf_sha256": sha_archivo(pdf) if pdf.exists() else "",
                        }

                        escribir_atomico(
                            state_path,
                            json.dumps(
                                state,
                                ensure_ascii=False,
                                indent=2,
                            ),
                        )

                        record.update(
                            estado="sincronizado",
                            document_id=doc_id,
                        )

                    else:
                        record["estado"] = "vacio"

                except BovedaModificada:
                    raise

                except Exception as error:
                    record["estado"] = "error"
                    record["detalle"] = str(error)

                    state["archivos"][rel] = {
                        "source_sha256": sha,
                        "source_size": path.stat().st_size,
                        "source_mtime_ns": path.stat().st_mtime_ns,
                        "error": True,
                        "detalle": str(error),
                    }

                    escribir_atomico(
                        state_path,
                        json.dumps(state, ensure_ascii=False, indent=2),
                    )
                    print(f"[ERROR] {rel}: {error}", flush=True)
                    continue

                registros.append(record)
                guardar_informe(
                    output,
                    registros,
                    len(candidatos),
                    False,
                )

            terminado = True

        except BovedaModificada as error:
            general = str(error)
            code = 2
            print(f"[ABORTADO] {general}", flush=True)

        except KeyboardInterrupt:
            general = "Proceso interrumpido por el usuario."
            code = 130
            print(f"[ABORTADO] {general}", flush=True)

        finally:
            migrador.converter = original_converter
            migrador.validar_fuente = original_validator

            guardar_informe(
                output,
                registros,
                len(candidatos),
                terminado,
                general,
            )

        return code
