# -*- coding: utf-8 -*-
"""Migrador 3.0: Obsidian -> PDF + Supabase, por lotes reanudables.

Uso: py -3 migrar_obsidian.py --nota "ruta absoluta o relativa a la boveda"
     py -3 migrar_obsidian.py --comprobar
     py -3 migrar_obsidian.py --todo

Configura Supabase con preparar_pdf.sql antes de la primera subida.
No ejecuta operaciones de red al importar este modulo.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import unicodedata
import uuid

from convertir_nota import convertir_nota, programa, ruta_pdf, EXPORTADOR, SALIDA

BASE = Path(__file__).resolve().parent
FILES_BUCKET = "repository-files"
IMAGES_BUCKET = "repository-images"
PDF_BUCKET = "repository-pdfs"
IGNORED_FOLDERS = {"imagenes", "imÃ¡genes", "assets", "attachments", "media", "pasted images"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
EMBED_PATTERN = re.compile(r"!\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")


@dataclass(frozen=True)
class Config:
    url: str
    key: str = field(repr=False)
    vault: Path
    output: Path
    exporter: str


def cargar_config() -> Config:
    try:
        from dotenv import load_dotenv
    except ImportError as error:
        raise RuntimeError("Instala dependencias: py -3 -m pip install supabase python-dotenv") from error
    load_dotenv(BASE / ".env")
    required = ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "OBSIDIAN_VAULT_PATH")
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise RuntimeError(f"Faltan variables en {BASE / '.env'}: {', '.join(missing)}")
    vault = Path(os.environ["OBSIDIAN_VAULT_PATH"]).expanduser().resolve()
    output = Path(os.environ.get("OBSIDIAN_PDF_OUTPUT", str(SALIDA))).expanduser().resolve()
    if not vault.is_dir():
        raise RuntimeError(f"No existe la boveda: {vault}")
    if output.is_relative_to(vault):
        raise RuntimeError("OBSIDIAN_PDF_OUTPUT debe estar fuera de la boveda.")
    return Config(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"],
                  vault, output, os.environ.get("OBSIDIAN_EXPORT_PATH", EXPORTADOR))


def clean_slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9._-]+", "-", text.lower()).strip("-") or "imagen"


def eq_or_is_null(query, column: str, value):
    return query.is_(column, "null") if value is None else query.eq(column, value)


def one_or_none(response, context: str):
    rows = response.data or []
    if len(rows) > 1:
        raise RuntimeError(f"Hay registros duplicados para {context}. Resuelve el duplicado antes de sincronizar.")
    return rows[0] if rows else None


class Migrador:
    def __init__(self, client, config: Config, converter=convertir_nota):
        self.client = client
        self.config = config
        self.converter = converter
        root_rows = (
            self.client
            .table("folders")
            .select("id,name,parent_id")
            .is_("parent_id", "null")
            .execute()
            .data
            or []
        )

        roots = [
            r for r in root_rows
            if str(r.get("name", "")).casefold() == "andre"
        ]

        if len(roots) > 1:
            raise RuntimeError(
                f"Hay varias carpetas raiz Andre en Supabase: {len(roots)}. "
                "Elimina el duplicado antes de sincronizar."
            )

        if len(roots) == 0:
            root_id = str(uuid.uuid4())
            self.client.table("folders").insert(
                {
                    "id": root_id,
                    "name": "Andre",
                    "parent_id": None,
                }
            ).execute()
            print("[OK] Carpeta raiz Andre creada en Supabase.", flush=True)
        else:
            root_id = roots[0]["id"]

        self.folder_map = {
            ".": root_id,
            "": root_id,
        }
        self.image_index = None
        self.image_cache = {}
        self.images_bucket_checked = False
        self.validar_fuente = lambda: None
        self.ultimo_documento = None
        self.forzar = False

    def comprobar(self):
        """Solo lectura: valida programas, columnas y buckets antes de compilar."""
        for executable in (self.config.exporter, "pandoc", "xelatex"):
            programa(executable)
        for name in ("callouts.lua", "estilos.tex"):
            if not (BASE / name).is_file():
                raise RuntimeError(f"Falta {name} junto a migrar_obsidian.py")
        try:
            self.client.table("documents").select(
                "id,original_name,folder_id,storage_path,content,extension,size_bytes,"
                "pdf_bucket,pdf_storage_path,pdf_size_bytes,pdf_updated_at"
            ).limit(1).execute()
            self.client.table("folders").select("id,name,parent_id").limit(1).execute()
            bucket = self.client.storage.get_bucket(PDF_BUCKET)
            self.client.storage.get_bucket(FILES_BUCKET)
        except Exception as error:
            raise RuntimeError(
                "Fallo la comprobacion de Supabase. Ejecuta preparar_pdf.sql y verifica "
                f"tu .env y el bucket {FILES_BUCKET}. Detalle: {error}"
            ) from error
        public = bucket.get("public") if isinstance(bucket, dict) else getattr(bucket, "public", None)
        if public is not False:
            raise RuntimeError(f"{PDF_BUCKET} debe ser privado; no se modifico su acceso.")
        print("[OK] Programas, columnas y buckets disponibles. No se han subido archivos.", flush=True)

    def resolve_folder_id(self, rel_path: str):
        """Misma jerarquia que el original, con error explicito si falla un padre."""
        rel_path = rel_path.replace("\\", "/")
        if rel_path in self.folder_map:
            return self.folder_map[rel_path]
        path = PurePosixPath(rel_path)
        parent_id = self.resolve_folder_id(path.parent.as_posix())
        query = self.client.table("folders").select("id").eq("name", path.name)
        query = eq_or_is_null(query, "parent_id", parent_id)
        row = one_or_none(query.limit(2).execute(), f"carpeta {rel_path}")
        if row is None:
            folder_id = str(uuid.uuid4())
            self.client.table("folders").insert(
                {"id": folder_id, "name": path.name, "parent_id": parent_id}
            ).execute()
        else:
            folder_id = row["id"]
        # Nunca cachear None para una carpeta que fallo: eso la moveria a raiz.
        self.folder_map[rel_path] = folder_id
        return folder_id

    def buscar_imagen(self, ref: str, nota: Path) -> Path:
        ruta = Path(ref.replace("\\", "/"))
        candidates = [ruta] if ruta.is_absolute() else [nota.parent / ruta, self.config.vault / ruta]
        for p in candidates:
            if p.is_file():
                return p.resolve()
        if self.image_index is None:
            self.image_index = {}
            def onerror(error):
                raise error
            for root, dirs, files in os.walk(self.config.vault, onerror=onerror, followlinks=False):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for name in files:
                    if Path(name).suffix.lower() in IMAGE_EXTENSIONS:
                        self.image_index.setdefault(name.casefold(), []).append(Path(root) / name)
        matches = self.image_index.get(ruta.name.casefold(), [])
        if len(matches) != 1:
            raise RuntimeError(f"Referencia de imagen no unica o inexistente: {ref}; coincidencias: {len(matches)}")
        return matches[0].resolve()

    def upload_image_and_get_url(self, image_path: Path) -> str:
        """Conserva el flujo de imagenes del visor Markdown existente."""
        data = image_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        key = (str(image_path), digest)
        if key in self.image_cache:
            return self.image_cache[key]
        if not self.images_bucket_checked:
            bucket = self.client.storage.get_bucket(IMAGES_BUCKET)
            public = bucket.get("public") if isinstance(bucket, dict) else getattr(bucket, "public", None)
            if public is not True:
                raise RuntimeError(
                    "El flujo Markdown existente necesita repository-images publico. "
                    "No se ha cambiado su acceso. Si prefieres retirar ese flujo, "
                    "primero hay que adaptar el visor a PDF."
                )
            self.images_bucket_checked = True
        storage_path = f"images/{clean_slug(image_path.stem)}-{digest}{image_path.suffix.lower()}"
        content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        self.upload(IMAGES_BUCKET, storage_path, data, content_type)
        url = self.client.storage.from_(IMAGES_BUCKET).get_public_url(storage_path)
        self.image_cache[key] = url
        return url

    def rewrite_embeds(self, content: str, nota: Path) -> str:
        def replace(match):
            ref = match.group(1).strip()
            if Path(ref).suffix.lower() not in IMAGE_EXTENSIONS:
                return match.group(0)
            url = self.upload_image_and_get_url(self.buscar_imagen(ref, nota))
            alt = ref.replace("[", "\\[").replace("]", "\\]")
            return f"![{alt}]({url})"
        return EMBED_PATTERN.sub(replace, content)

    def upload(self, bucket: str, path: str, data: bytes, content_type: str):
        self.client.storage.from_(bucket).upload(
            path, data, {"content-type": content_type, "upsert": "true"}
        )

    def sincronizar_nota(self, nota: Path):
        nota = Path(nota).resolve()

        if (
            not nota.is_relative_to(self.config.vault)
            or not nota.is_file()
            or nota.suffix.lower() != ".md"
        ):
            raise RuntimeError(
                f"La nota debe ser un archivo .md dentro de la boveda: {nota}"
            )

        source = nota.read_bytes()

        if not source.strip():
            print(f"[OMITIDA] Nota vacia: {nota}", flush=True)
            return None

        source_sha256 = hashlib.sha256(source).hexdigest()
        source_rel_path = nota.relative_to(self.config.vault).as_posix()
        rel_folder = nota.relative_to(self.config.vault).parent.as_posix()
        folder_id = self.resolve_folder_id(rel_folder)

        # Primero buscamos por identidad del archivo.
        query = (
            self.client
            .table("documents")
            .select("id,storage_path,folder_id,source_sha256,source_rel_path")
            .eq("source_sha256", source_sha256)
        )

        existing = one_or_none(
            query.limit(2).execute(),
            f"SHA {nota.name}"
        )

        # Compatibilidad con documentos antiguos que aun no tienen SHA.
        if existing is None:
            query = (
                self.client
                .table("documents")
                .select("id,storage_path,folder_id,source_sha256,source_rel_path")
                .eq("original_name", nota.name)
            )
            existing = one_or_none(
                eq_or_is_null(query, "folder_id", folder_id)
                .limit(2)
                .execute(),
                f"nota antigua {nota.name}"
            )

        # Documento antiguo sin SHA:
        # lo asociamos al SHA actual SIN volver a subirlo.
        if (
            existing
            and not self.forzar
            and not existing.get("source_sha256")
        ):
            doc_id = existing["id"]

            payload = {
                "title": nota.stem,
                "original_name": nota.name,
                "extension": "md",
                "size_bytes": len(source),
                "content": source.decode("utf-8-sig"),
                "folder_id": folder_id,
                "source_sha256": source_sha256,
                "source_rel_path": source_rel_path,
            }

            response = (
                self.client
                .table("documents")
                .update(payload)
                .eq("id", doc_id)
                .execute()
            )

            if not response.data:
                raise RuntimeError(
                    "No se pudo asociar el SHA al documento existente."
                )

            self.ultimo_documento = {
                "id": doc_id,
                **payload,
                "storage_path": existing.get("storage_path"),
            }

            print(
                f"[REUBICADO/REGISTRADO] {nota.name} | document_id={doc_id}",
                flush=True,
            )
            return doc_id

        # Documento existente y contenido sin cambios:
        # SOLO actualizar estructura/metadatos.
        if (
            existing
            and not self.forzar
            and existing.get("source_sha256") == source_sha256
        ):
            doc_id = existing["id"]

            payload = {
                "title": nota.stem,
                "original_name": nota.name,
                "extension": "md",
                "size_bytes": len(source),
                "content": source.decode("utf-8-sig"),
                "folder_id": folder_id,
                "source_sha256": source_sha256,
                "source_rel_path": source_rel_path,
            }

            response = (
                self.client
                .table("documents")
                .update(payload)
                .eq("id", doc_id)
                .execute()
            )

            if not response.data:
                raise RuntimeError(
                    "No se pudo actualizar la ubicacion del documento."
                )

            self.ultimo_documento = {
                "id": doc_id,
                **payload,
                "storage_path": existing.get("storage_path"),
            }

            print(
                f"[SIN SUBIDA] {nota.name} | documento sin cambios",
                flush=True,
            )
            return doc_id

        # Documento nuevo o modificado:
        # aqui SI se convierte y se sube.
        raw = source.decode("utf-8-sig")

        pdf = self.converter(
            vault=self.config.vault,
            nota=nota,
            salida=self.config.output,
            exportador=self.config.exporter,
            abrir=False,
        )

        self.validar_fuente()

        if nota.read_bytes() != source:
            raise RuntimeError(
                "La nota cambio durante la conversion."
            )

        pdf_data = Path(pdf).read_bytes()

        if not pdf_data.startswith(b"%PDF-"):
            raise RuntimeError(
                "El conversor no produjo un PDF valido."
            )

        doc_id = existing["id"] if existing else str(uuid.uuid4())

        pdf_path = (
            f"documents/{doc_id}/"
            f"{hashlib.sha256(pdf_data).hexdigest()}.pdf"
        )

        md_path = (
            existing.get("storage_path")
            if existing
            else f"documents/{doc_id}.md"
        )

        self.upload(
            PDF_BUCKET,
            pdf_path,
            pdf_data,
            "application/pdf",
        )

        self.upload(
            FILES_BUCKET,
            md_path,
            source,
            "text/markdown; charset=utf-8",
        )

        payload = {
            "title": nota.stem,
            "original_name": nota.name,
            "extension": "md",
            "storage_path": md_path,
            "size_bytes": len(source),
            "content": raw,
            "folder_id": folder_id,
            "pdf_bucket": PDF_BUCKET,
            "pdf_storage_path": pdf_path,
            "pdf_size_bytes": len(pdf_data),
            "pdf_updated_at": datetime.now(timezone.utc).isoformat(),
            "source_sha256": source_sha256,
            "source_rel_path": source_rel_path,
        }

        if existing:
            response = (
                self.client
                .table("documents")
                .update(payload)
                .eq("id", doc_id)
                .execute()
            )
        else:
            response = (
                self.client
                .table("documents")
                .insert({"id": doc_id, **payload})
                .execute()
            )

        if not response.data:
            raise RuntimeError(
                "Supabase no devolvio el documento guardado."
            )

        self.ultimo_documento = {
            "id": doc_id,
            **payload,
        }

        print(
            f"[SUBIDO] {nota.name} | document_id={doc_id}",
            flush=True,
        )

        return doc_id

    def sincronizar_pdf(self, archivo: Path):
        archivo = archivo.resolve()

        if (
            not archivo.is_relative_to(self.config.vault)
            or not archivo.is_file()
            or archivo.suffix.lower() != ".pdf"
        ):
            raise RuntimeError(
                f"El archivo debe ser un PDF dentro de la boveda: {archivo}"
            )

        datos = archivo.read_bytes()

        if not datos.startswith(b"%PDF-"):
            raise RuntimeError(
                f"El archivo no contiene una cabecera PDF valida: {archivo}"
            )

        source_sha256 = hashlib.sha256(datos).hexdigest()
        source_rel_path = archivo.relative_to(self.config.vault).as_posix()

        rel_folder = archivo.relative_to(self.config.vault).parent.as_posix()
        folder_id = self.resolve_folder_id(rel_folder)

        # Buscar primero por SHA.
        query = (
            self.client
            .table("documents")
            .select("id,storage_path,folder_id,source_sha256,source_rel_path")
            .eq("source_sha256", source_sha256)
        )

        existing = one_or_none(
            query.limit(2).execute(),
            f"SHA {archivo.name}"
        )

        # Compatibilidad con documentos antiguos.
        if existing is None:
            query = (
                self.client
                .table("documents")
                .select("id,storage_path,folder_id,source_sha256,source_rel_path")
                .eq("original_name", archivo.name)
            )

            existing = one_or_none(
                eq_or_is_null(query, "folder_id", folder_id)
                .limit(2)
                .execute(),
                str(archivo),
            )

        # Documento antiguo:
        # registrar SHA y nueva ubicacion SIN subir nuevamente.
        if (
            existing
            and not self.forzar
            and not existing.get("source_sha256")
        ):
            doc_id = existing["id"]

            payload = {
                "title": archivo.stem,
                "original_name": archivo.name,
                "extension": "pdf",
                "size_bytes": len(datos),
                "folder_id": folder_id,
                "source_sha256": source_sha256,
                "source_rel_path": source_rel_path,
            }

            response = (
                self.client
                .table("documents")
                .update(payload)
                .eq("id", doc_id)
                .execute()
            )

            if not response.data:
                raise RuntimeError(
                    "No se pudo asociar el SHA al PDF existente."
                )

            self.ultimo_documento = {
                "id": doc_id,
                **payload,
                "storage_path": existing.get("storage_path"),
            }

            print(
                f"[REUBICADO/REGISTRADO] {archivo.name} | document_id={doc_id}",
                flush=True,
            )

            return doc_id

        # Documento sin cambios:
        # NO tocar Storage.
        if (
            existing
            and not self.forzar
            and existing.get("source_sha256") == source_sha256
        ):
            doc_id = existing["id"]

            payload = {
                "title": archivo.stem,
                "original_name": archivo.name,
                "extension": "pdf",
                "size_bytes": len(datos),
                "folder_id": folder_id,
                "source_sha256": source_sha256,
                "source_rel_path": source_rel_path,
            }

            response = (
                self.client
                .table("documents")
                .update(payload)
                .eq("id", doc_id)
                .execute()
            )

            if not response.data:
                raise RuntimeError(
                    "No se pudo actualizar la ubicacion del PDF."
                )

            self.ultimo_documento = {
                "id": doc_id,
                **payload,
                "storage_path": existing.get("storage_path"),
            }

            print(
                f"[SIN SUBIDA] {archivo.name} | documento sin cambios",
                flush=True,
            )

            return doc_id

        # Documento nuevo o modificado.
        doc_id = existing["id"] if existing else str(uuid.uuid4())

        storage_path = (
            existing.get("storage_path")
            if existing
            else f"documents/{doc_id}.pdf"
        )

        self.upload(
            FILES_BUCKET,
            storage_path,
            datos,
            "application/pdf",
        )

        payload = {
            "title": archivo.stem,
            "original_name": archivo.name,
            "extension": "pdf",
            "storage_path": storage_path,
            "size_bytes": len(datos),
            "content": "",
            "folder_id": folder_id,
            "pdf_bucket": None,
            "pdf_storage_path": None,
            "pdf_size_bytes": None,
            "pdf_updated_at": None,
            "source_sha256": source_sha256,
            "source_rel_path": source_rel_path,
        }

        if existing:
            response = (
                self.client
                .table("documents")
                .update(payload)
                .eq("id", doc_id)
                .execute()
            )
        else:
            response = (
                self.client
                .table("documents")
                .insert({"id": doc_id, **payload})
                .execute()
            )

        if not response.data:
            raise RuntimeError(
                "Supabase no devolvio el PDF guardado."
            )

        self.ultimo_documento = {
            "id": doc_id,
            **payload,
        }

        print(
            f"[SUBIDO] {archivo.name} | document_id={doc_id}",
            flush=True,
        )

        return doc_id

    def archivos(self):
        def onerror(error):
            raise error

        vault = self.config.vault.resolve()

        # Solo se sincronizan las carpetas principales cuyo nombre
        # termina en "SEMESTRE". Todo lo demas queda fuera.
        carpetas_semestre = {
            p.resolve()
            for p in vault.iterdir()
            if p.is_dir()
            and not p.name.startswith(".")
            and p.name.strip().casefold().endswith("semestre")
        }

        for carpeta_raiz in sorted(carpetas_semestre, key=lambda p: p.name.casefold()):
            for root, dirs, files in os.walk(
                carpeta_raiz,
                onerror=onerror,
                followlinks=False,
            ):
                dirs[:] = sorted(
                    d for d in dirs
                    if not d.startswith(".")
                )

                for name in sorted(files):
                    if (
                        not name.startswith(".")
                        and Path(name).suffix.lower() in {".md", ".pdf"}
                    ):
                        yield Path(root) / name

    def notas(self):
        return (p for p in self.archivos() if p.suffix.lower() == ".md")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--nota", help="Ruta absoluta o relativa a la boveda")
    group.add_argument("--todo", action="store_true", help="Procesar todos los Markdown y PDF conservando carpetas")
    group.add_argument("--comprobar", action="store_true", help="Verificar configuracion sin subir archivos")
    parser.add_argument("--forzar", action="store_true", help="Reconvertir incluso notas ya sincronizadas")
    args = parser.parse_args()
    print("Migrador 3.0 - lote reanudable e informe de errores", flush=True)
    config = None
    try:
        config = cargar_config()
        try:
            from supabase import create_client
        except ImportError as error:
            raise RuntimeError("Instala dependencias: py -3 -mpip install supabase python-dotenv") from error
        migrador = Migrador(create_client(config.url, config.key), config)
        migrador.comprobar()
        if args.comprobar:
            return 0
        from lote_obsidian import ejecutar_lote
        if args.nota:
            nota = Path(args.nota)
            if not nota.is_absolute():
                nota = config.vault / nota
            if nota.suffix.lower() == ".md":
                migrador.sincronizar_nota(nota)
            elif nota.suffix.lower() == ".pdf":
                migrador.sincronizar_pdf(nota)
            else:
                raise RuntimeError(f"Tipo de archivo no soportado: {nota}")
            return 0
        return ejecutar_lote(migrador, list(migrador.archivos()), forzar=args.forzar)
    except KeyboardInterrupt:
        print("\nProceso interrumpido.", file=sys.stderr)
        return 130
    except Exception as error:
        message = str(error)
        if config:
            message = message.replace(config.key, "[CLAVE OCULTA]")
        print(f"[ERROR] {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())






