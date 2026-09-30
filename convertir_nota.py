"""Convierte una nota de Obsidian a PDF. Python >= 3.10; sin paquetes pip.

La funcion convertir_nota se puede reutilizar luego desde un watcher.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit
from normalizar_latex import normalizar_latex

BASE = Path(__file__).resolve().parent
VAULT = Path(r"C:\Users\USUARIO\OneDrive\Andre")
NOTA = Path(r"C:\Users\USUARIO\OneDrive\Andre\NON-REGULAR SEMESTER\Algebraic Structure\Clases 1M\Class 6- 30-04-2026.md")
SALIDA = Path(r"C:\Users\USUARIO\Desktop\Bobeda\PDFs")
EXPORTADOR = r"C:\Users\USUARIO\OneDrive - Universidad Central del Ecuador\Escritorio\Bobeda\obsidian-export-x86_64-pc-windows-msvc\obsidian-export.exe"


def programa(nombre: str) -> str:
    encontrado = shutil.which(nombre)
    if encontrado:
        return encontrado
    p = Path(nombre)
    if p.is_file():
        return str(p.resolve())
    raise RuntimeError(f"No se encuentra el programa: {nombre}")


def ejecutar(comando: list[str], carpeta: Path, registro: Path) -> None:
    """Registra la salida completa y muestra actividad cada 15 segundos."""
    with registro.open("ab") as log:
        log.write(("\nCOMANDO: " + json.dumps(comando, ensure_ascii=False) + "\n").encode("utf-8"))
        log.flush()
        proceso = subprocess.Popen(comando, cwd=carpeta, stdout=log,
                                   stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        try:
            while True:
                try:
                    codigo = proceso.wait(timeout=15)
                    break
                except subprocess.TimeoutExpired:
                    print("  Sigue trabajando. Si MiKTeX abre una ventana, revisala.", flush=True)
        except KeyboardInterrupt:
            proceso.terminate()
            try:
                proceso.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait()
            raise
    if codigo:
        ultimas = registro.read_text(encoding="utf-8", errors="replace").splitlines()[-35:]
        # La causa debe llegar tambien al informe del lote, no solo a la consola.
        detalle = "\n".join(ultimas)
        raise RuntimeError(f"El proceso termino con codigo {codigo}. Registro: {registro}\n{detalle}")


def preparar_imagenes(documento: dict, nota: Path, vault: Path) -> tuple[int, int]:
    """Resuelve rutas del AST de Pandoc sin sustituir texto mediante regex."""
    imagenes = 0
    enlaces_notas = 0
    indice = None

    def error_recorrido(error):
        # No elegir una imagen si no pudimos revisar toda la boveda.
        raise error

    def resolver_imagen(src: str) -> Path:
        nonlocal indice
        url = urlsplit(src)
        es_unidad_windows = len(src) > 1 and src[1] == ':'
        if url.scheme and url.scheme.lower() != 'file' and not es_unidad_windows:
            raise RuntimeError(
                f"Imagen no local: {src}. Descargala en la boveda y enlazala desde la nota."
            )
        texto = unquote(src if es_unidad_windows else url.path).replace('\\', '/')
        if url.scheme.lower() == 'file':
            if url.netloc and url.netloc.lower() != 'localhost':
                texto = '//' + url.netloc + texto
            elif len(texto) > 2 and texto[0] == '/' and texto[2] == ':':
                texto = texto[1:]
        ruta = Path(texto)
        candidatos = [ruta] if ruta.is_absolute() else [nota.parent / ruta, vault / ruta]
        for p in candidatos:
            if p.is_file():
                return p.resolve()

        # Algunas rutas Windows pierden separadores al pasar por Markdown
        # (por ejemplo, ..\..\ se puede leer como ....\). No adivinamos
        # cuantos niveles habia: solo recuperamos un nombre unico en la boveda.
        nombre = ruta.name
        if indice is None:
            print('  Buscando adjuntos por nombre dentro de la boveda...', flush=True)
            indice = {}
            for carpeta, dirs, archivos in os.walk(vault, onerror=error_recorrido, followlinks=False):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for archivo in archivos:
                    p = Path(carpeta) / archivo
                    indice.setdefault(archivo.casefold(), []).append(p)
        coincidencias = indice.get(nombre.casefold(), [])
        if len(coincidencias) == 1:
            encontrada = coincidencias[0].resolve()
            print(f'  Imagen localizada por nombre: {encontrada}', flush=True)
            return encontrada
        if len(coincidencias) > 1:
            opciones = '\n'.join(str(p) for p in coincidencias)
            raise RuntimeError(
                f'Ruta de imagen no resuelta: {src}\nHay varias imagenes llamadas {nombre}:\n'
                f'{opciones}\nIndica en la nota una ruta que identifique la imagen correcta.'
            )
        raise RuntimeError(
            f'Imagen no encontrada: {src}\nNombre buscado: {nombre}\n'
            f'Buscada desde: {nota.parent}\nTambien se busco dentro de: {vault}\n'
            'Comprueba que el adjunto exista y este disponible localmente en OneDrive.'
        )

    def visitar(nodo):
        nonlocal imagenes, enlaces_notas
        if isinstance(nodo, dict):
            if nodo.get("t") == "Image":
                destino = nodo["c"][2]
                src = destino[0]
                encontrada = resolver_imagen(src)
                destino[0] = encontrada.as_posix()
                imagenes += 1
            elif nodo.get("t") == "Link":
                if urlsplit(nodo["c"][2][0]).path.lower().endswith(".md"):
                    enlaces_notas += 1
            for valor in nodo.values():
                visitar(valor)
        elif isinstance(nodo, list):
            for valor in nodo:
                visitar(valor)

    visitar(documento)
    # Mantiene los metadatos de la nota; usa espanol si no tiene idioma.
    documento.setdefault("meta", {}).setdefault("lang", {"t": "MetaString", "c": "es"})
    return imagenes, enlaces_notas


def ruta_pdf(vault: Path, nota: Path, salida: Path) -> Path:
    relativo = nota.relative_to(vault)
    if nota.suffix.lower() == ".pdf":
        return salida / relativo
    # No pisar un PDF original que comparta nombre con una nota Markdown.
    if nota.with_suffix(".pdf").is_file():
        return salida / relativo.with_name(relativo.name + ".pdf")
    return salida / relativo.with_suffix(".pdf")


def _corregir_latex_basico(texto: str) -> str:
    import re

    # Unicode matematico -> LaTeX. Usamos escapes \uXXXX para que este
    # archivo sea puro ASCII y no se corrompa al copiar/pegar por consola.
    reemplazos = {
        "\u22c5": r"\cdot ",        # ⋅
        "\u2202": r"\partial ",     # ∂
        "\u2260": r"\ne ",          # ≠
        "\u222b": r"\int ",         # ∫
        "\u03bc": r"\mu ",          # μ
        "\U0001d707": r"\mu ",      # 𝜇
        "\u03c8": r"\psi ",         # ψ
        "\U0001d713": r"\psi ",     # 𝜓
        "\u03c6": r"\varphi ",      # φ
        "\U0001d711": r"\varphi ", # 𝜑
        "\u03b2": r"\beta ",        # β
        "\U0001d6fd": r"\beta ",   # 𝛽
        "\u03bb": r"\lambda ",      # λ
        "\U0001d706": r"\lambda ",# 𝜆
        "\U0001d45d": "p",          # 𝑝
        "\U0001d45e": "q",          # 𝑞
        "\u2234": r"\therefore ",   # ∴
        "\u26a1": r"\star ",        # ⚡
    }
    for origen, destino in reemplazos.items():
        texto = texto.replace(origen, destino)

    def _sustituir_N_uso(fragmento: str) -> str:
        # \N como abreviatura de \mathbb{N} SOLO cuando se usa en prosa,
        # nunca cuando \N es el nombre que se esta definiendo (eso se
        # protege por separado en el bucle de abajo).
        return re.sub(r"\\N\b", r"\\mathbb{N}", fragmento)

    # --- Universalizar \newcommand{\X}{CUERPO} ---
    # En vez de decidir a mano que macros "ya existen" en LaTeX (fragil y
    # depende del entorno de MiKTeX), convertimos TODA definicion en el
    # patron estandar providecommand + renewcommand: define el comando si
    # no existia, y siempre lo redefine con el cuerpo de la nota. Funciona
    # igual si el nombre ya estaba tomado por LaTeX/paquetes o no, y
    # tambien resuelve sin error el caso de un mismo nombre definido dos
    # veces en la misma nota (la segunda definicion simplemente gana).
    patron_def = re.compile(r"\\newcommand\s*\{\s*\\([a-zA-Z]+)\s*\}\s*(?:\[\d+\]\s*)?\{")

    def _extraer_cuerpo(s: str, inicio_llave: int):
        profundidad = 0
        for i in range(inicio_llave, len(s)):
            if s[i] == "{":
                profundidad += 1
            elif s[i] == "}":
                profundidad -= 1
                if profundidad == 0:
                    return s[inicio_llave + 1:i], i + 1
        raise ValueError("Llaves no balanceadas en una definicion \\newcommand.")

_RE_NEWCOMMAND_INICIO = re.compile(r"\\newcommand\s*\{\s*\\([a-zA-Z]+)\s*\}\s*(?:\[\d+\]\s*)?\{")


def _definiciones_newcommand_puras(cuerpo: str):
    """Si 'cuerpo' consiste UNICAMENTE en una o mas definiciones
    \\newcommand{\\X}{...} separadas solo por espacios, retorna la lista de
    (nombre, cuerpo_macro). Si hay cualquier otro contenido (una formula real),
    retorna None para no tocar esa formula."""
    definiciones = []
    pos, n = 0, len(cuerpo)
    while pos < n:
        while pos < n and cuerpo[pos].isspace():
            pos += 1
        if pos >= n:
            break
        m = _RE_NEWCOMMAND_INICIO.match(cuerpo, pos)
        if not m:
            return None
        nombre = m.group(1)
        cuerpo_macro, fin = _extraer_cuerpo(cuerpo, m.end() - 1)
        definiciones.append((nombre, cuerpo_macro))
        pos = fin
    return definiciones if definiciones else None


def extraer_macros(documento: dict) -> list[str]:
    """Busca bloques matematicos que son SOLO definiciones \\newcommand
    (el patron que usan las notas para declarar atajos como \\s, \\l, \\N).

    Pandoc los deja dentro de \\[...\\] (modo matematico), que abre un grupo
    de LaTeX: cualquier \\newcommand ahi dentro se olvida al cerrar el grupo.
    Por eso los sacamos del cuerpo del documento y los devolvemos aparte, para
    inyectarlos como preambulo real (--include-in-header) donde valen para
    toda la nota. El nodo se vacia en el AST para no dejar una formula vacia.
    """
    macros = []

    def visitar(nodo):
        if isinstance(nodo, dict):
            if nodo.get("t") == "Math":
                contenido = nodo["c"][1]
                definiciones = _definiciones_newcommand_puras(contenido.strip())
                if definiciones is not None:
                    for nombre, cuerpo_macro in definiciones:
                        macros.append(f"\\let\\{nombre}\\relax")
                        macros.append(f"\\newcommand{{\\{nombre}}}{{{cuerpo_macro}}}")
                    nodo["c"][1] = ""
            for valor in nodo.values():
                visitar(valor)
        elif isinstance(nodo, list):
            for item in nodo:
                visitar(item)

    visitar(documento)
    return macros

def convertir_nota(vault: Path, nota: Path, salida: Path,
                   exportador: str = EXPORTADOR, abrir: bool = False,
                   boveda_preparada: Path | None = None) -> Path:
    vault, nota, salida = (Path(p).expanduser().resolve() for p in (vault, nota, salida))
    if not vault.is_dir():
        raise RuntimeError(f"No existe la boveda: {vault}")
    if not nota.is_file() or nota.suffix.lower() != ".md":
        raise RuntimeError(f"No existe la nota Markdown: {nota}")
    if not nota.is_relative_to(vault):
        raise RuntimeError("La nota debe estar dentro de la boveda indicada.")
    if salida.is_relative_to(vault):
        raise RuntimeError("Elige una carpeta de salida fuera de la boveda.")
    exportador = programa(exportador)
    pandoc, xelatex = programa("pandoc"), programa("xelatex")
    filtro, estilos = BASE / "callouts.lua", BASE / "estilos.tex"
    for p in (filtro, estilos):
        if not p.is_file():
            raise RuntimeError(f"Falta {p.name}. Extrae todos los archivos del ZIP juntos.")

    destino = ruta_pdf(vault, nota, salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    registro = destino.with_suffix(".conversion.log")
    registro.write_text(f"Nota: {nota}\nDestino: {destino}\n", encoding="utf-8")
    print(f"Conversor 1.3 - separadores Markdown protegidos\nNota: {nota}\nPDF:  {destino}", flush=True)
    # El temporal se crea junto al PDF para reemplazarlo al finalizar sin
    # tocar la version anterior si exportacion o compilacion fallan.
    with tempfile.TemporaryDirectory(prefix="conversion_", dir=destino.parent) as temporal:
        trabajo = Path(temporal)
        exportados = trabajo / "markdown"
        exportados.mkdir()
        if boveda_preparada is None:
            print("  Preparando copia temporal de la nota...", flush=True)
            boveda_temporal = trabajo / "boveda"
            nota_temporal = boveda_temporal / nota.relative_to(vault)
            nota_temporal.parent.mkdir(parents=True, exist_ok=True)

            datos_nota = nota.read_bytes()
            try:
                contenido_nota = normalizar_latex(datos_nota.decode("utf-8-sig"))
                nota_temporal.write_text(contenido_nota, encoding="utf-8", newline="\n")
                # Copiar los archivos adjuntos referenciados por la nota.
                import re
                referencias = set()

                for match in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", contenido_nota):
                    referencias.add(match.strip())

                for match in re.findall(r"!\[\[([^\]]+)\]\]", contenido_nota):
                    referencias.add(match.strip().split("|")[0].strip())

                for referencia in referencias:
                    if referencia.startswith(("http://", "https://")):
                        continue

                    nombre = Path(referencia).name
                    candidatos = list(vault.rglob(nombre))

                    for origen in candidatos:
                        if origen.is_file():
                            destino_adjunto = boveda_temporal / origen.relative_to(vault)
                            destino_adjunto.parent.mkdir(parents=True, exist_ok=True)
                            destino_adjunto.write_bytes(origen.read_bytes())

            except UnicodeDecodeError:
                nota_temporal.write_bytes(datos_nota)
        else:
            boveda_temporal = Path(boveda_preparada)
        nota_temporal = boveda_temporal / nota.relative_to(vault)
        print("[1/3] Preparando nota y referencias con obsidian-export...", flush=True)
        ejecutar([exportador, str(boveda_temporal), "--start-at", str(nota_temporal), str(exportados)], trabajo, registro)
        # obsidian-export puede omitir un embed faltante y terminar con codigo 0.
        # Su aviso debe detener la publicacion, no producir un PDF incompleto.
        export_log = registro.read_text(encoding="utf-8", errors="replace")
        advertencia = re.search(r"(?im)^\s*warning:.*(?:embed|image|attachment)", export_log)
        if advertencia:
            detalle = export_log[advertencia.start():].strip().replace(str(boveda_temporal), str(vault))
            raise RuntimeError(
                "obsidian-export emitio una advertencia sobre un adjunto o contenido incrustado. No se reemplazo el PDF ni se subio esta nota.\n"
                + detalle + f"\nRegistro completo: {registro}"
            )
        archivos = list(exportados.rglob("*.md"))
        if len(archivos) != 1:
            raise RuntimeError(f"Se esperaba una nota exportada y se encontraron {len(archivos)}. Revisa exclusiones de la boveda.")
        exportado = archivos[0]
        ast = trabajo / "documento.json"
        print("[2/3] Preparando imagenes y contenido matematico...", flush=True)
        ejecutar([pandoc, str(exportado), "--from=markdown-implicit_figures", "--to=json", "--output", str(ast)], trabajo, registro)
        documento = json.loads(ast.read_text(encoding="utf-8"))

        def corregir_unicode(obj):
            if isinstance(obj, str):
                return (
                    obj.replace("∂", r"\partial ")
                       .replace("⋅", r"\cdot ")
                       .replace("≠", r"\ne ")
                )
            if isinstance(obj, list):
                return [corregir_unicode(x) for x in obj]
            if isinstance(obj, dict):
                return {k: corregir_unicode(v) for k, v in obj.items()}
            return obj

        documento = corregir_unicode(documento)
        cantidad, enlaces = preparar_imagenes(documento, nota, vault)
        macros = extraer_macros(documento)
        ast.write_text(json.dumps(documento, ensure_ascii=False), encoding="utf-8")
        print(f"  Imagenes locales: {cantidad}", flush=True)
        if enlaces:
            print(f"  Enlaces a notas: {enlaces}. Se conserva su destino .md; la navegacion web se configurara despues.", flush=True)
        encabezados = ["--include-in-header", str(estilos)]
        if macros:
            print(f"  Macros \\newcommand movidas al preambulo: {len(macros) // 2}", flush=True)
            macros_path = trabajo / "macros_nota.tex"
            macros_path.write_text("\n".join(macros) + "\n", encoding="utf-8")
            encabezados += ["--include-in-header", str(macros_path)]
        temporal_pdf = trabajo / "resultado.pdf"
        print("[3/3] Compilando PDF con Pandoc y XeLaTeX...", flush=True)
        ejecutar([pandoc, str(ast), "--from=json", "--standalone",
                  "--lua-filter", str(filtro), *encabezados,
                  "--pdf-engine", xelatex, "--verbose", "--fail-if-warnings",
                  "--resource-path", os.pathsep.join([str(nota.parent), str(vault)]),
                  "-V", "papersize=a4", "-V", "geometry:margin=22mm", "-V", "fontsize=11pt",
                  "--output", str(temporal_pdf)], trabajo, registro)
        with temporal_pdf.open("rb") as f:
            if f.read(5) != b"%PDF-":
                raise RuntimeError("La salida no es un PDF valido.")
        try:
            os.replace(temporal_pdf, destino)
        except PermissionError as error:
            raise RuntimeError(f"No se pudo actualizar {destino}. Cierra el visor del PDF y vuelve a ejecutar.") from error
    print(f"\nPDF generado correctamente:\n{destino}\nRegistro: {registro}", flush=True)
    if abrir and os.name == "nt":
        try:
            os.startfile(str(destino))
        except OSError as error:
            print(f"PDF guardado; no se pudo abrir automaticamente: {error}", flush=True)
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=VAULT)
    parser.add_argument("--nota", type=Path, default=NOTA)
    parser.add_argument("--salida", type=Path, default=SALIDA)
    parser.add_argument("--exportador", default=EXPORTADOR)
    parser.add_argument("--abrir", action="store_true")
    args = parser.parse_args()

    # Las rutas relativas de la nota y salida se resuelven desde el vault.
    if not args.nota.is_absolute():
        args.nota = args.vault / args.nota

    if not args.salida.is_absolute():
        args.salida = args.vault / args.salida

    try:
        convertir_nota(args.vault, args.nota, args.salida, args.exportador, args.abrir)
    except KeyboardInterrupt:
        print("\nConversion interrumpida. Puedes volver a ejecutarla.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError) as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())





