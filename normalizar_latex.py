"""Adaptacion conservadora de LaTeX en notas Markdown antes de obsidian-export.

No corrige delimitadores matematicos desequilibrados ni interpreta un documento
LaTeX completo. Conserva codigo y matematicas ya delimitadas.
"""
from pathlib import Path
import os
import re
import shutil
import hashlib
import time


def normalizar_latex(texto: str) -> str:
    salida = []
    i = 0
    # Conservar el frontmatter literalmente.
    front = re.match(r"\A---\r?\n[\s\S]*?\r?\n(?:---|\.\.\.)(?:\r?\n|$)", texto)
    if front:
        salida.append(front[0])
        i = front.end()

    def cierre(delimitador, desde):
        while True:
            j = texto.find(delimitador, desde)
            if j < 0:
                return -1
            k = j - 1
            while k >= 0 and texto[k] == "\\":
                k -= 1
            if (j - 1 - k) % 2 == 0:
                return j
            desde = j + len(delimitador)

    while i < len(texto):
        resto = texto[i:]
        if i == 0 or texto[i - 1] == "\n":
            fence = re.match(r" {0,3}(`{3,}|~{3,})[^\n]*(?:\n|$)", resto)
            if fence:
                run = fence[1]
                end = re.search(r"(?m)^ {0,3}" + re.escape(run[0]) + "{" + str(len(run)) + r",}[ \t]*(?:\n|$)", resto[fence.end():])
                n = fence.end() + end.end() if end else len(resto)
                salida.append(resto[:n]); i += n; continue
            if resto.startswith("    ") or resto.startswith("\t"):
                end = resto.find("\n")
                n = end + 1 if end >= 0 else len(resto)
                salida.append(resto[:n]); i += n; continue
            # obsidian-export 25.3 puede interpretar '---\n## Titulo' como
            # metadatos incluso dentro del cuerpo. Separar la regla del bloque
            # siguiente evita esa lectura sin borrar contenido. El frontmatter
            # inicial ya se conservo arriba; no tocar subrayados Setext.
            separador = re.match(r" {0,3}---[ \t]*\r?\n", resto)
            inicio_anterior = texto.rfind("\n", 0, max(0, i - 1)) + 1
            anterior_vacia = i > 0 and not texto[inicio_anterior:i-1].strip()
            if separador and anterior_vacia:
                siguiente = resto[separador.end():]
                if siguiente and not re.match(r"[ \t]*\r?\n", siguiente):
                    salto = "\r\n" if separador[0].endswith("\r\n") else "\n"
                    salida.append(separador[0] + salto)
                    i += separador.end(); continue
        if texto[i] == "`":
            run = re.match(r"`+", resto)[0]
            end = re.search(r"(?<!`)" + re.escape(run) + r"(?!`)", resto[len(run):])
            if end:
                n = len(run) + end.end()
                salida.append(resto[:n]); i += n; continue
        if texto[i] == "$":
            delim = "$$" if resto.startswith("$$") else "$"
            j = cierre(delim, i + len(delim))
            if j >= 0:
                n = j + len(delim)
                salida.append(texto[i:n]); i = n; continue
        if resto.startswith("\\(") or resto.startswith("\\["):
            display = resto.startswith("\\[")
            j = cierre("\\]" if display else "\\)", i + 2)
            if j >= 0:
                body = texto[i + 2:j].strip()
                salida.append("\n\n$$\n" + body + "\n$$\n\n" if display else "$" + body + "$")
                i = j + 2; continue
        env = re.match(r"\\begin\{(equation\*?|displaymath|align\*?|gather\*?|multline\*?)\}", resto)
        if env:
            endmark = "\\end{" + env[1] + "}"
            j = texto.find(endmark, i + env.end())
            if j >= 0:
                body = texto[i + env.end():j].strip()
                name = env[1].rstrip("*")
                inner = {"align": "aligned", "gather": "gathered", "multline": "gathered"}.get(name)
                if inner:
                    body = "\\begin{" + inner + "}\n" + body + "\n\\end{" + inner + "}"
                salida.append("\n\n$$\n" + body + "\n$$\n\n")
                i = j + len(endmark); continue
        heading = re.match(r"\\(section|subsection|subsubsection|paragraph)\*?\s*\{", resto)
        if heading:
            start = i + heading.end()
            j, depth = start, 1
            while j < len(texto) and depth:
                if texto[j] == "\\":
                    j += 2; continue
                if texto[j] == "{": depth += 1
                if texto[j] == "}": depth -= 1
                j += 1
            if depth == 0:
                level = {"section": 1, "subsection": 2, "subsubsection": 3, "paragraph": 4}[heading[1]]
                title = normalizar_latex(texto[start:j-1]).strip().replace("\n", " ")
                previo = "".join(salida)
                # Evita un encabezado vacio si la nota ya llevaba '### \\section'.
                previo = re.sub(r"(?m)^ {0,3}#{1,6}[ \t]+$", "", previo)
                salida = [previo]
                salida.append("\n\n" + "#" * level + " " + title + "\n\n")
                i = j
                while i < len(texto) and texto[i] in " \t": i += 1
                continue
        # Un escape literal no debe convertirse en el comienzo de un comando.
        if texto[i] == "\\" and i + 1 < len(texto):
            salida.append(texto[i:i+2]); i += 2; continue
        salida.append(texto[i]); i += 1
    return "".join(salida)


def preparar_boveda(vault: Path, destino: Path, inventario: dict | None = None) -> Path:
    """Copia temporal: Markdown normalizado; adjuntos enlazados o copiados.

    Nunca se escribe en un adjunto enlazado ni en una nota original.
    Los hardlinks evitan duplicar imagenes grandes; copy2 es el respaldo cuando
    el sistema de archivos no permite enlazar. Se omiten carpetas internas.
    """
    ultimo_aviso = time.monotonic()
    cantidad = 0

    def copiar(src, dst):
        nonlocal ultimo_aviso, cantidad
        source = Path(src)
        antes = source.stat()
        if source.suffix.lower() == ".md":
            datos = source.read_bytes()
            try:
                contenido = normalizar_latex(datos.decode("utf-8-sig"))
            except UnicodeDecodeError:
                # Una nota mal codificada debe fallar individualmente al procesar
                # el lote, no impedir preparar todas las demas notas.
                Path(dst).write_bytes(datos)
            else:
                Path(dst).write_text(contenido, encoding="utf-8", newline="\n")
            digest = hashlib.sha256(datos).hexdigest()
        else:
            try:
                os.link(src, dst)
            except OSError:
                shutil.copy2(src, dst)
            digest = None
            if inventario is not None:
                hasher = hashlib.sha256()
                with source.open("rb") as entrada:
                    for bloque in iter(lambda: entrada.read(1024 * 1024), b""):
                        hasher.update(bloque)
                digest = hasher.hexdigest()
        despues = source.stat()
        if (antes.st_size, antes.st_mtime_ns) != (despues.st_size, despues.st_mtime_ns):
            raise RuntimeError(f"La boveda cambio mientras se preparaba: {source}. Repite la ejecucion.")
        if inventario is not None:
            inventario[source.relative_to(vault).as_posix()] = {
                "sha256": digest, "size": despues.st_size, "mtime_ns": despues.st_mtime_ns,
            }
        cantidad += 1
        if time.monotonic() - ultimo_aviso >= 10:
            print(f"  Preparando boveda: {cantidad} archivos revisados...", flush=True)
            ultimo_aviso = time.monotonic()
        return dst

    def ignorar(carpeta, nombres):
        return [n for n in nombres if (Path(carpeta) / n).is_dir() and (
            n.startswith(".") or (Path(carpeta) / n).is_symlink()
            or getattr(os.path, "isjunction", lambda _: False)(Path(carpeta) / n)
        )]

    shutil.copytree(vault, destino, copy_function=copiar, ignore=ignorar)
    return destino
