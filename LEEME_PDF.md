# Obsidian → PDF → repositorio web

Actualización del 24-09-2026: migrador 3.0, conversor 1.3 y visor PDF.
Este paquete actualiza la integración que ya tienes configurada. No es un proyecto React independiente.

## Qué hace

| Archivo de la bóveda | Resultado |
| --- | --- |
| `.md` | Compila un PDF con texto, fórmulas, callouts e imágenes locales; lo sube a `repository-pdfs` y actualiza su documento. |
| `.pdf` existente | Lo copia y sube sin recompilar, usando `repository-files` y el lector de documentos existente. |
| `.png`, `.jpg`, `.jpeg` referenciados | Se incorporan al PDF de la nota. No se crean documentos de galería separados. |

Se mantiene la jerarquía de carpetas de cada documento en la web. Las carpetas vacías o que solo contienen adjuntos no se crean como carpetas nuevas del catálogo. `.obsidian` y otras carpetas internas ocultas se omiten.

Los originales permanecen en `C:\Users\USUARIO\OneDrive\Andre`. Los PDF de lectura se guardan bajo `C:\Users\USUARIO\Desktop\Bobeda\PDFs`, respetando las subcarpetas. Si conviven `Clase.md` y `Clase.pdf`, el resultado del Markdown se llama `Clase.md.pdf` para conservar ambos.

La web muestra el PDF compilado. Su paginación y tipografía dependen de la plantilla; no es una captura idéntica de la interfaz de Obsidian.

## 1. Instalar esta actualización

1. Guarda los cambios en VS Code. Detén con Ctrl+C cualquier migración o servidor Vite que siga ejecutándose.
2. Extrae TODO el ZIP en una carpeta diferente del proyecto.
3. Ejecuta `INSTALAR.cmd` desde esa carpeta extraída.

El instalador copia los archivos en:

`C:\Users\USUARIO\Desktop\repositorio-react-completo\repositorio-react`

Antes de sustituirlos guarda un respaldo en `respaldos/lector-pdf-FECHA`. Actualiza el migrador, el conversor y el visor. Conserva `.env`, `package.json`, `src/main.tsx`, la configuración del cliente Supabase y los archivos `callouts.lua`/`estilos.tex` existentes. Si estos dos últimos faltan, instala los incluidos. No requiere paquetes nuevos respecto a la integración ya instalada.

Si el proyecto está en otra ruta, ejecuta desde la carpeta extraída:

```powershell
py -3 .\instalar_parche.py "RUTA_COMPLETA_DEL_PROYECTO"
```

La instalación solo cambia archivos locales; no sube documentos ni despliega funciones.

## 2. Procesar toda la bóveda

Cierra los PDF locales de salida que estén abiertos en un visor. Deja disponibles en el equipo los archivos de OneDrive y termina de editar las notas antes de iniciar el lote.

```powershell
Set-Location -LiteralPath "C:\Users\USUARIO\Desktop\repositorio-react-completo\repositorio-react"
py -3 .\migrar_obsidian.py --todo
```

La consola debe empezar con `Migrador 3.0 - lote reanudable e informe de errores`. Este comando comprueba la configuración, prepara una sola copia temporal de la bóveda y procesa todos los Markdown y PDF existentes. Muestra el progreso `[n/total]` y un resumen final.

Un fallo de conversión o subida se registra y el lote continúa con los demás documentos. Una imagen faltante o ambigua impide publicar esa nota incompleta. La versión PDF anterior de esa nota continúa disponible si ya existía. Si detecta cambios en archivos durante el lote, se detiene: repite el comando cuando termines de editar.

La preparación inicial lee los archivos y puede tardar con una bóveda grande o con OneDrive. Un archivo inaccesible durante esa preparación puede impedir iniciar el lote; el informe lo indica. No se corrige borrando notas.

Si una terminal antigua de VS Code vuelve a indicar que no encuentra Pandoc o XeLaTeX, actualiza su PATH y repite el comando:

```powershell
$env:Path += ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
$env:Path += ";" + [Environment]::GetEnvironmentVariable("Path", "User")
```

## Reanudar e informe único

Puedes detener el lote con Ctrl+C y volver a ejecutar `--todo`. El estado local registra cada documento después de confirmar la subida y la actualización de la base de datos. Si la bóveda y el código no cambiaron, se omiten los éxitos que conservan su PDF local y su registro remoto; se reintentan los fallidos y pendientes.

La comprobación de cambios es conservadora: cualquier cambio en notas, adjuntos, estilos, código o versiones de las herramientas invalida el estado del lote. Se recompilan los documentos para incluir posibles dependencias entre notas. No es todavía una reconstrucción selectiva por dependencias. La primera ejecución con 3.0 vuelve a procesar los documentos subidos con versiones anteriores.

El resumen y las causas de error se guardan en:

- `C:\Users\USUARIO\Desktop\Bobeda\PDFs\informe_migracion.json`
- `C:\Users\USUARIO\Desktop\Bobeda\PDFs\informe_migracion.csv`

Si hay errores, comparte primero el JSON completo: reúne archivos afectados, causas, categorías, progreso y rutas a registros. No necesitas copiar la consola nota por nota. Los registros de conversión completos quedan junto a cada PDF. El informe puede contener fragmentos de tus notas en los mensajes de compilación.

El estado se guarda en `.estado_migracion.json`, dentro de la salida. No contiene la clave de Supabase. La reanudación compara los registros remotos, pero no descarga cada objeto para comprobarlo. Si borraste objetos directamente de Storage, fuerza su regeneración/subida:

```powershell
py -3 .\migrar_obsidian.py --todo --forzar
```

`--comprobar` sigue disponible para revisar herramientas, columnas y buckets sin subir archivos. `--nota "RUTA"` permite procesar un archivo concreto, pero no es necesario para la migración completa.

## 3. Abrir los documentos desde React

Desde la carpeta del proyecto:

```powershell
npm.cmd run build
```

Si termina correctamente:

```powershell
npm.cmd run dev
```

Abre http://localhost:5173/, inicia sesión y recarga con Ctrl+F5. Una nota sincronizada debe abrir su PDF. El visor permite abrirlo en otra pestaña y descargarlo. Si aparece `Vista Markdown`, ese documento aún no tiene PDF sincronizado; revisa su resultado en el informe.

La función privada `serve-pdf` debe estar desplegada para leer los PDF generados. Si ya desplegaste la del paquete anterior, no requiere cambios. Si falta, utiliza el archivo completo `supabase/functions/serve-pdf/index.ts` del paquete para crear una función con el nombre exacto `serve-pdf`; es independiente y no importa `handler.mjs`. Mantén la verificación JWT y el bucket `repository-pdfs` privado. Conserva `serve-document`, que sirve los PDF originales y otros documentos.

No hace falta ejecutar SQL nuevo: se utilizan las columnas y buckets que ya funcionaron en la subida de Class 6. Las claves privilegiadas permanecen en Python/Edge Functions; no se colocan en variables `VITE_*`.

Actualizar localhost no publica la página alojada: esa página necesita su despliegue habitual después de compilar.

## Correcciones incluidas

- Separadores Markdown `---` del cuerpo que obsidian-export 25.3.0 confundía con YAML: se añade una línea vacía en la copia temporal, conservando los originales, el frontmatter inicial, el código y los títulos Setext.
- Rutas de imagen con espacios, codificación URL y separadores Windows: resolución por ruta o nombre único dentro de la bóveda; los nombres ambiguos se reportan.
- Advertencias de adjuntos omitidos por obsidian-export: se tratan como errores, aunque el exportador termine con código cero.
- Encabezados LaTeX y entornos matemáticos habituales: se normalizan antes de exportar para conservar las fórmulas.
- Carpetas con el mismo nombre en ramas diferentes: se resuelven usando la jerarquía completa.
- Rutas originales de Storage: se respeta `canonical_storage_path`; las revisiones del PDF generado usan su ruta independiente.
- Visor Markdown anterior: vuelve a mostrar las imágenes con URL permitida que ya estuvieran subidas. Las nuevas conversiones incorporan las imágenes al PDF privado y no suben adjuntos públicos separados.

## Alcance

Esta entrega sincroniza mediante el comando. La automatización al guardar con un watcher sigue pendiente.

Borrar o mover archivos locales no elimina automáticamente los documentos antiguos de Supabase. Las revisiones antiguas de PDF tampoco se limpian automáticamente. No se han realizado borrados remotos desde esta actualización.

Se adaptan `section`, `subsection`, `subsubsection`, `paragraph`, `\(...\)`, `\[...\]` y los entornos `equation`, `displaymath`, `align`, `gather`, `multline` con sus variantes con asterisco. La numeración automática de esos entornos no se conserva. No es un compilador de documentos LaTeX completos ni puede corregir automáticamente expresiones matemáticas mal escritas. Los enlaces a otras notas conservan su destino `.md`; no se transforman todavía en navegación entre documentos del repositorio web.

Los límites de tamaño configurados en los buckets continúan aplicándose a libros y otros PDF grandes. Un rechazo se muestra en el informe y no bloquea los demás documentos.

## Validación realizada

- Once pruebas automatizadas: reanudación, interrupciones, fallos de subida, cambios de fuente, bloqueo de ejecuciones simultáneas, jerarquías, colisión MD/PDF, informe con causa del exportador y redacción de la clave configurada.
- Lote real con obsidian-export, Pandoc y XeLaTeX: dos notas compiladas y un PDF original importado; dos fallos intencionales aislados; repetición con los tres éxitos omitidos y los errores reintentados. Fórmulas, callout e imagen comprobados visualmente en el PDF generado. Originales sin cambios.
- Reproducción y corrección del error YAML de la nota completa suministrada, conservando sus 36 referencias de imagen. Esos adjuntos reales no estaban disponibles: esta comprobación no verifica su contenido visual.
- React: comprobación TypeScript de los archivos modificados y pruebas del visor en DOM simulado. Los componentes del proyecto no suministrados se sustituyeron solo en el entorno de prueba, no en el paquete. El build del proyecto completo se realiza en tu equipo.
- Instalador: respaldo de archivos existentes, copia de los nuevos módulos y conservación de configuración/estilos.

Las pruebas de subida usan un cliente Supabase simulado. No se ha ejecutado esta actualización contra tu bóveda completa ni contra tu Supabase real, ni se ha desplegado tu web desde aquí.

Para repetir las pruebas sin conexión desde la carpeta extraída:

```powershell
py -3 -m unittest discover -s tests -p test_lote.py -v
```
