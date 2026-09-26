# Repositorio académico · React + Supabase

Código fuente completo para abrir en Visual Studio Code, modificarlo y publicarlo con tus propias cuentas. Esta versión usa Google y una lista de lectores autorizados; no utiliza la contraseña compartida del sitio anterior. No está conectada a ningún proyecto real ni modifica el sitio que se publicó antes.

**Empieza por los pasos 1–2 para abrir la interfaz. Completa 3–6 para activar el acceso y los archivos. El paso 8 publica tu propia web.**

## Qué incluye

- Interfaz React + TypeScript con un índice lateral, carpetas, búsqueda por título y lector central.
- Acceso con Google. Una cuenta administradora y lectores que autorizas por correo.
- Subida y eliminación de documentos desde «Administrar».
- PDF, Markdown con fórmulas matemáticas, código LaTeX, Word, ZIP e imágenes.
- Archivos privados de hasta **20 MiB**; vista previa de texto hasta 2 MiB.
- Reglas SQL de seguridad y una función de descarga que comprueba la cuenta en cada petición.
- Pruebas automatizadas de permisos y descarga.

Todos los lectores activos acceden a la misma biblioteca. Esta primera versión no asigna permisos por documento ni restringe a una sola sesión simultánea.

## 1. Abrir el proyecto en Visual Studio Code

Instala [Node.js](https://nodejs.org/en/download), versión 22.12 o posterior, y Visual Studio Code. Se ha comprobado con Node 24.19.0.

1. Extrae el ZIP.
2. En VS Code selecciona **Archivo → Abrir carpeta** y abre `repositorio-react`, donde está `package.json`.
3. Abre **Terminal → Nueva terminal**. Los comandos siguientes se ejecutan en esa carpeta.

```powershell
node --version
npm --version
npm ci
npm run dev
```

Abre [la interfaz local](http://localhost:5173). Mantén esa terminal abierta. Para detener el servidor pulsa **Ctrl+C**.

Sin configurar `.env`, verás la pantalla «Configura tu biblioteca»: es el comportamiento esperado. No abras `index.html` con doble clic ni con Live Server; este proyecto se ejecuta con Vite.

Si PowerShell impide ejecutar `npm.ps1`, usa `npm.cmd ci` y `npm.cmd run dev`, o elige una terminal **Command Prompt** en VS Code. No necesitas cambiar la política de ejecución de Windows.

## 2. Crear el archivo de configuración

Copia `.env.example` con el nombre `.env`. En PowerShell puedes hacerlo con:

```powershell
Copy-Item .env.example .env
```

El contenido será:

```dotenv
VITE_SUPABASE_URL=https://TU_PROYECTO.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_TU_CLAVE_PUBLICA
VITE_APP_NAME=Biblioteca de Andre Edou
```

Sustituye los ejemplos después de crear el proyecto del paso 3. Reinicia `npm run dev` cuando cambies `.env`.

**Solo la clave pública va en `VITE_SUPABASE_PUBLISHABLE_KEY`.** Las variables `VITE_*` se incorporan al navegador. Nunca pongas ahí una clave `service_role`, una clave `sb_secret_...`, la contraseña de la base de datos o el secreto OAuth de Google. La clave pública puede ser visible porque los permisos se comprueban en el servidor.

## 3. Crear Supabase y cargar la base de datos

1. Abre [Supabase](https://supabase.com/dashboard) y crea un proyecto nuevo dedicado a esta biblioteca.
2. Obtén su URL y su clave **Publishable** desde la conexión/API del proyecto y completa `.env`. Una clave pública `anon` heredada también puede usarse; nunca la `service_role`.
3. En **SQL Editor**, pega el contenido completo de `supabase/01_schema.sql` y ejecútalo una vez.
4. Abre `supabase/02_admin.sql` en VS Code. Reemplaza `CAMBIA_ESTO_POR_TU_CORREO@gmail.com` por el correo exacto de tu cuenta de Google.
5. Ejecuta ese segundo archivo en SQL Editor.

El primer script crea tablas, permisos y el contenedor privado `repository-files`. El segundo preautoriza al administrador. El identificador de tu cuenta se vinculará automáticamente al iniciar sesión por primera vez.

Usa un proyecto nuevo: otras políticas permisivas en un proyecto existente podrían ampliar el acceso. No vuelvas a ejecutar el script inicial para actualizar la biblioteca; conserva los datos y aplica migraciones nuevas para cambios futuros. Si aparece «already exists», comprueba qué script ejecutaste antes de repetirlo.

Los permisos usan RLS de PostgreSQL y funciones con contexto controlado. [Referencia oficial de RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).

## 4. Configurar «Continuar con Google»

Esta configuración se hace una vez en tus cuentas. No debes compartir tus contraseñas conmigo.

1. En Supabase, abre **Authentication → Sign In / Providers → Google** y localiza la URL de callback de tu proyecto. Habitualmente tiene la forma `https://TU_PROYECTO.supabase.co/auth/v1/callback`; copia la que muestre el panel.
2. En [Google Cloud Console](https://console.cloud.google.com/), crea/selecciona un proyecto y configura **Google Auth Platform**: nombre de la aplicación, correo de contacto y audiencia adecuada.
3. Crea un cliente OAuth de tipo **Web application**.
4. En los orígenes JavaScript autorizados agrega `http://localhost:5173`.
5. En las URI de redirección autorizadas agrega el **callback de Supabase**, no el puerto de Vite.
6. Copia el **Client ID** y **Client Secret** en el proveedor Google de Supabase y habilítalo. El secreto queda en Supabase, nunca en React.
7. Limita los permisos solicitados a identidad básica: `openid`, correo y perfil. Esta biblioteca no accede a Google Drive.
8. Si la aplicación Google está en modo de prueba, agrega como usuarios de prueba las cuentas que vayas a utilizar. Para ampliar la audiencia, completa los requisitos que indique Google.
9. En Supabase, desactiva el proveedor de acceso por email/contraseña y el inicio anónimo si están activos. Conserva Google habilitado. Permite la creación de cuentas por Google: crear una cuenta de autenticación **no** da acceso a la biblioteca; la lista SQL decide quién entra.

En **Authentication → URL Configuration** de Supabase, usa inicialmente:

| Ajuste | Valor local |
|---|---|
| Site URL | `http://localhost:5173/` |
| Redirect URLs | `http://localhost:5173/` |

No son la misma configuración: **Google redirige a Supabase; Supabase redirige a tu web.** El cliente utiliza PKCE y gestiona el retorno en la ruta raíz. Para las pruebas usa el mismo navegador en el que iniciaste sesión.

[Google con Supabase](https://supabase.com/docs/guides/auth/social-login/auth-google) · [URLs de retorno](https://supabase.com/docs/guides/auth/redirect-urls) · [OAuth de Google](https://developers.google.com/identity/protocols/oauth2/web-server).

## 5. Publicar la función de descarga protegida

Aunque ejecutes React en tu computadora, esta función se ejecuta en tu proyecto de Supabase. Es necesaria para abrir y descargar los documentos como lector.

En otra terminal de VS Code, desde la carpeta del proyecto:

```powershell
npx supabase login
npx supabase projects list
```

Copia el **Project Ref** de tu proyecto. En los comandos siguientes sustituye `TU_PROJECT_REF`; es el identificador del proyecto, no su contraseña ni la URL completa.

```powershell
npx supabase secrets set "ALLOWED_ORIGINS=http://localhost:5173" --project-ref TU_PROJECT_REF
npx supabase functions deploy serve-document --project-ref TU_PROJECT_REF --use-api
```

La opción `--use-api` permite publicar sin un entorno Docker local. El código y `supabase/config.toml` ya están incluidos; no necesitas ejecutar `supabase init` sobre esta carpeta.

La función usa variables de servidor que Supabase proporciona: `SUPABASE_URL`, `SUPABASE_ANON_KEY` y `SUPABASE_SERVICE_ROLE_KEY`. No copies la última en `.env` del frontend.

En `config.toml`, `verify_jwt = false` desactiva únicamente la comprobación heredada del gateway. **La función hace su propia verificación obligatoria con `auth.getUser(token)`**, comprueba el permiso vigente y consulta los metadatos con el token del usuario antes de leer el archivo. No elimines estas comprobaciones.

[Publicación de funciones](https://supabase.com/docs/guides/functions/deploy) · [Variables del servidor](https://supabase.com/docs/guides/functions/secrets) · [Configuración de funciones](https://supabase.com/docs/guides/functions/function-configuration).

## 6. Primer ingreso y uso

1. Reinicia `npm run dev` si cambiaste `.env`.
2. Abre [localhost:5173](http://localhost:5173).
3. Pulsa **Continuar con Google** y elige el correo que preautorizaste en `02_admin.sql`.
4. Abre **Administrar → Documentos**. Crea una carpeta y sube `ejemplos/primer-apunte.md` para comprobar las fórmulas.
5. En **Administrar → Personas**, escribe el correo Google de un lector y pulsa **Autorizar lector**. Esta acción no envía invitaciones por correo.
6. Comparte la dirección de tu web una vez publicada. Esa persona entra con su propia cuenta.

Una cuenta aún no autorizada verá su correo y el botón «Comprobar autorización». Después de que la autorices puede pulsarlo sin volver a iniciar sesión. Puedes revocar o restablecer lectores desde la misma lista.

## 7. Formatos y límites actuales

| Formato | Comportamiento |
|---|---|
| PDF | Vista previa y descarga del original |
| MD / Markdown | Texto formateado, listas, tablas, código y fórmulas `$...$` / `$$...$$` |
| TEX / BIB / STY / CLS / TXT | Vista del código fuente y descarga |
| DOC / DOCX | Descarga para abrir en Word o LibreOffice |
| ZIP | Conserva una carpeta completa, por ejemplo una bóveda de Obsidian |
| PNG / JPG / JPEG / WebP | Vista previa y descarga |

LaTeX no se compila en el servidor. Puedes subir el `.tex` y su PDF como documentos separados. Los enlaces `[[...]]`, transclusiones, complementos, callouts específicos de Obsidian y diagramas Mermaid todavía no se interpretan. Las imágenes incrustadas en Markdown se muestran como referencias de texto; los originales pueden subirse aparte o conservarse en un ZIP. No hay sincronización automática con Obsidian.

El texto tiene un límite de vista previa de 2 MiB para evitar bloquear el navegador. El tamaño de cada archivo se limita a 20 MiB. El almacenamiento total y la transferencia dependen del plan de tu proveedor; esta aplicación no añade una cuota global.

## 8. Publicar la interfaz en la web

La interfaz puede alojarse como sitio estático porque la autenticación y el almacenamiento están en Supabase. Aquí se describe una publicación manual en Netlify, sin obligarte a crear un repositorio de GitHub.

Primero comprueba el proyecto y genera los archivos web con tu `.env` ya configurado:

```powershell
npm test
npm run build
```

Se crea `dist`. No edites esa carpeta: se regenera a partir de `src`.

1. Entra en tu cuenta de [Netlify](https://app.netlify.com/).
2. Usa su publicación manual y sube la carpeta **`dist`**, que contiene `index.html` y `assets`. No subas la raíz del proyecto, `.env` ni `node_modules`.
3. Obtendrás una URL del tipo `https://TU-BIBLIOTECA.netlify.app`.
4. En Supabase **URL Configuration**, cambia **Site URL** por la URL final con `/` al final y agrégala a **Redirect URLs**. Puedes mantener localhost en la lista para desarrollar.
5. En Google agrega el origen HTTPS final a los orígenes JavaScript autorizados. El callback de Supabase no cambia.
6. Agrega el origen final a la función:

```powershell
npx supabase secrets set "ALLOWED_ORIGINS=http://localhost:5173,https://TU-BIBLIOTECA.netlify.app" --project-ref TU_PROJECT_REF
```

Escribe los orígenes sin `/` final ni rutas. Si cambia el dominio, actualiza también esta lista. La interfaz necesita ser accesible para que los lectores lleguen a su pantalla de Google; la protección de los documentos reside en Supabase.

Para actualizar después: modifica `src`, ejecuta `npm run build` y sube el nuevo `dist` en **Deploys del mismo sitio**. Mantén la URL. La base de datos y los archivos permanecen en Supabase.

Si posteriormente conectas GitHub a Netlify, el archivo `netlify.toml` configura el build. Introduce las mismas tres variables públicas `VITE_*` en el entorno de compilación de Netlify. Los archivos `_headers` y `_redirects` incluidos proporcionan cabeceras y retorno a `index.html`.

[Compilación y publicación con Vite](https://vite.dev/guide/static-deploy.html) · [Publicaciones manuales de Netlify](https://docs.netlify.com/deploy/create-deploys/).

## 9. Qué archivo editar para cada mejora

| Archivo | Responsabilidad |
|---|---|
| `src/App.tsx` | Sesión, índice lateral, búsqueda, navegación y acciones |
| `src/styles.css` | Colores, tamaños, escritorio y móvil |
| `src/components/Reader.tsx` | Vista de PDF, Markdown, fórmulas y texto |
| `src/components/AdminPanel.tsx` | Subida, carpetas y lectores |
| `src/components/Modal.tsx` | Ventanas de administración y confirmación |
| `src/lib/repository.ts` | Operaciones de datos y archivos |
| `src/lib/supabase.ts` | Cliente y configuración pública |
| `src/types.ts` | Estructura de documentos, carpetas y lectores |
| `supabase/01_schema.sql` | Instalación inicial de base de datos y permisos |
| `supabase/functions/serve-document/` | Verificación de sesión y entrega del archivo |
| `tests/` | Pruebas de acceso y descarga |

Puedes formatear los cambios con `npm run format`. Las versiones exactas de las dependencias y `package-lock.json` permiten repetir la instalación con `npm ci`.

## 10. Seguridad, comprobaciones y alcance

- El permiso se vincula a un UUID de cuenta después de verificar el correo y la identidad Google. El navegador no puede asignarse roles.
- Los lectores solo ven sus propios datos de autorización y los documentos de la biblioteca.
- Las políticas niegan a lectores el acceso directo a Storage. La función entrega los bytes tras verificar acceso; no devuelve URLs firmadas que el lector pueda reenviar.
- El administrador sí puede gestionar Storage. Es una cuenta de confianza.
- Revocar un lector bloquea sus siguientes consultas y descargas aunque su sesión de Google siga abierta. La interfaz revisa el permiso cada 30 segundos y al recuperar el foco.
- Un documento ya descargado, copiado o mostrado no se puede recuperar remotamente. No se impide compartir una cuenta voluntariamente ni realizar capturas.
- La sesión del cliente utiliza el almacenamiento del navegador gestionado por Supabase. El cierre de sesión afecta a ese navegador. No se incluye la regla de una única sesión simultánea.
- El lector Markdown no ejecuta HTML crudo; KaTeX se configura sin confiar en comandos externos.

**Verificación realizada:** compilación TypeScript/Vite y 16 pruebas automatizadas correctas. Las pruebas SQL se ejecutan en PostgreSQL embebido (PGlite), con esquemas de prueba que representan `auth` y `storage`. Las pruebas de descarga ejercitan el manejador con respuestas controladas.

**Pendiente en tu entorno:** el flujo OAuth real de Google, el despliegue de la función, la integración con Supabase Storage y la vista previa en tu navegador. No se han usado credenciales reales para simular que esa conexión ya existe.

Antes de compartir documentos reales, prueba con dos cuentas: una autorizada y otra sin permiso. La segunda debe ver «sin autorización». Revoca la primera y comprueba que ya no descarga al realizar una petición nueva. No desactives RLS para corregir errores.

## Problemas frecuentes

| Síntoma | Qué revisar |
|---|---|
| «Configura tu biblioteca» | `.env` en la raíz, valores reales y reinicio de Vite |
| Google: `redirect_uri_mismatch` | Callback exacto de Supabase en Google Cloud |
| Google: acceso restringido en prueba | Usuarios de prueba y audiencia en Google |
| Tu cuenta no tiene autorización | Correo exacto en `02_admin.sql`, cuenta elegida y script ejecutado |
| No aparece «Administrar» | La fila correspondiente debe tener `role = 'admin'` |
| No se puede consultar tablas | `01_schema.sql` ejecutado en el mismo proyecto de `.env` |
| Vista previa/descarga falla | Función desplegada, `ALLOWED_ORIGINS`, sesión y permiso activo |
| Error CORS | Origen exacto de la web en `ALLOWED_ORIGINS`, sin barra final |
| Funciona localmente, falla en la web | URL final en Google, Supabase Redirect URLs y ALLOWED_ORIGINS |
| PDF no aparece | Prueba «Descargar»; el visor depende del soporte de PDF del navegador |
| Cambios no aparecen en internet | Reconstruye y publica el nuevo `dist` del mismo sitio |
| `relation already exists` | El esquema inicial ya se ejecutó; no lo repitas sobre tus datos |

Para consultar esta guía con formato en VS Code, abre el archivo y pulsa **Ctrl+Shift+V**.
