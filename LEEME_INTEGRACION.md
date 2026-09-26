# Integracion Obsidian -> PDF -> Supabase

## Estado

La conversion local 1.1 ya fue validada por Andre con su clase y todas sus
imagenes. Este paquete integra esa funcion en el migrador compartido.
La subida real se comprobara en tu equipo; el asistente no ejecuto operaciones
contra tu proyecto Supabase.

## 1. Preparar el proyecto

En esta carpeta:

```text
C:\Users\USUARIO\Desktop\repositorio-react-completo\repositorio-react
```

Guarda una copia del migrador actual antes de reemplazarlo. Por ejemplo,
desde PowerShell dentro de esa carpeta:

```powershell
$respaldo = "migrar_obsidian_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".bak"
Copy-Item -LiteralPath .\migrar_obsidian.py -Destination $respaldo
```

Extrae los archivos del paquete junto a tu .env. migrar_obsidian.py,
convertir_nota.py, callouts.lua y estilos.tex deben quedar juntos.
El ZIP no contiene .env y no reemplaza tus credenciales.

El nuevo migrador conserva estas variables de tu .env:

- SUPABASE_URL
- SUPABASE_SECRET_KEY
- OBSIDIAN_VAULT_PATH

Si quieres cambiar las rutas de herramientas o salida, agrega las dos lineas
de variables_pdf.example al .env. Los valores por defecto ya corresponden
a tu carpeta Bobeda. Guarda el .env en VS Code antes de ejecutar.

Instala dependencias si no estan disponibles en el Python que vas a usar:

```powershell
py -3 -m pip install -r .\requirements_pdf.txt
```

SUPABASE_SECRET_KEY se usa solo en este script local. No debe llevar prefijo
VITE_ ni colocarse en componentes React. Mantiene la forma de autenticacion
del script que compartiste.

## 2. Preparar Supabase

Abre el SQL Editor del mismo proyecto donde estan folders y documents.
Pega y ejecuta TODO el archivo preparar_pdf.sql.

La migracion agrega cuatro columnas opcionales a documents y crea
repository-pdfs como bucket privado. Puede repetirse. No borra registros,
no modifica el acceso de los buckets existentes y no amplia politicas RLS.
Si repository-pdfs ya existe como publico, se detiene sin aplicar cambios.

| Campo nuevo | Contenido |
|---|---|
| pdf_bucket | repository-pdfs |
| pdf_storage_path | Ruta del objeto PDF dentro del bucket |
| pdf_size_bytes | Tamano real del PDF |
| pdf_updated_at | Fecha UTC de la sincronizacion correcta |

## 3. Verificar sin subir archivos

En la terminal de tu proyecto:

```powershell
py -3 .\migrar_obsidian.py --comprobar
```

Este modo consulta Supabase y revisa programas y columnas. No crea carpetas,
no genera PDF ni sube archivos. La comprobacion de repository-images se hace
si una nota necesita subir imagenes para el visor Markdown existente.

## 4. Sincronizar la clase que ya convertiste

```powershell
py -3 .\migrar_obsidian.py --nota "C:\Users\USUARIO\OneDrive\Andre\NON-REGULAR SEMESTER\Algebraic Structure\Clases 1M\Class 6- 30-04-2026.md"
```

La operacion genera el PDF, resuelve la carpeta jerarquica, busca el documento
por nombre original y carpeta, sube PDF/Markdown y actualiza el registro.
Un documento existente conserva su id; uno nuevo recibe un id nuevo.

El PDF local queda bajo Desktop\Bobeda\PDFs conservando las subcarpetas.
En Storage se usa una ruta por id de documento y hash de contenido.
Al final debe aparecer [OK] y el document_id.

Puedes ejecutar esta consulta en Supabase para verificar el registro:

```sql
select id, title, original_name, pdf_bucket, pdf_storage_path,
       pdf_size_bytes, pdf_updated_at
from public.documents
where original_name = 'Class 6- 30-04-2026.md';
```

## 5. Resto de la boveda

Despues de validar esa nota, el modo completo es:

```powershell
py -3 .\migrar_obsidian.py --todo
```

Recorre las notas secuencialmente. Si una falla, informa el error y continua
con las demas. El codigo de salida es distinto de cero si hubo fallos.
Compila de nuevo cada nota seleccionada; todavia no hay watcher ni cache de
dependencias. Ejecuta una sola instancia del migrador a la vez.
Las notas de la raiz tambien se procesan. Se mantienen las exclusiones de
carpetas de adjuntos del script original.

## Compatibilidad durante esta etapa

Se conservan content, storage_path, extension='md', original_name y folder_id.
El contenido Markdown sigue reescribiendo sus imagenes al bucket existente
repository-images, como hacia tu script. Por eso el visor actual puede seguir
leyendo esos campos mientras integramos la visualizacion PDF.

Las imagenes tambien quedan dentro del PDF. Cuando el visor PDF este adaptado,
podremos retirar la subida separada de imagenes del flujo de lectura.
El paquete no crea repository-images ni cambia sus permisos.

La logica heredada de reemplazo de embeds en Markdown no pretende renderizar
todos los plugins de Obsidian; la conversion PDF utiliza obsidian-export.

## Comportamiento ante fallos

- Un fallo de conversion no escribe registros ni sube archivos.
- Un fallo al resolver una carpeta no envia la nota a la raiz por accidente.
- Un fallo de subida no cambia las rutas activas en documents.
- Si falla el ultimo guardado en la base, pueden quedar objetos subidos sin
  referencia. No se borran automaticamente.
- Cada revision usa una ruta derivada de sus bytes. Las versiones anteriores
  no se borran ni se sobrescriben por otras distintas. Esto consume espacio
  hasta que se implemente una limpieza controlada.
- La hora interna de un PDF puede cambiar sus bytes entre compilaciones.
  Por eso repetir una compilacion puede producir otra revision del objeto,
  aunque conserva el mismo documento en la tabla.
- DB y Storage no comparten una transaccion. Subir primero y actualizar la
  fila al final evita publicar una ruta cuyo archivo todavia no se ha subido.
- Si existen carpetas/documentos duplicados con la misma identidad, se informa
  del problema en vez de elegir el primero.

## Lo que falta en React

El migrador deja disponible pdf_bucket + pdf_storage_path. El frontend necesita
leer esos campos y solicitar una URL firmada con la sesion del usuario para
mostrar el PDF. No se debe guardar una URL firmada como ubicacion permanente.
Se deben revisar las politicas de lectura existentes antes de agregar la
politica del nuevo bucket. Un bucket privado no basta si ya existen politicas
amplias sobre storage.objects.

Para adaptar esa parte hacen falta el componente que muestra la nota, la
consulta/tipo de documents y las reglas de acceso que ya utiliza el repositorio.
El watcher con watchdog queda para despues de validar conversion y subida.

## Validacion del paquete

La funcion de conversion ya se probo con obsidian-export 25.3.0 y XeLaTeX,
y el usuario confirmo el resultado en Windows. La integracion se prueba con
un cliente Supabase simulado: actualizacion de id, orden de subidas/guardado,
errores de conversion/subida/base, carpeta raiz y padres con error.
No se ha probado contra las restricciones SQL reales de tu proyecto.

Referencias oficiales consultadas:

- https://supabase.com/docs/reference/python/storage-from-upload
- https://supabase.com/docs/reference/python/storage-getbucket
- https://supabase.com/docs/reference/python/update
