// Ejecutar con Node.js desde la carpeta del proyecto. No requiere instalar paquetes.
// Solo contiene la URL y la clave PUBLICA facilitadas por el propietario.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { pathToFileURL } = require('node:url');
const { spawn } = require('node:child_process');

const config = {
  VITE_SUPABASE_URL: 'https://vjyrcahrtpqmqhhmktrz.supabase.co',
  VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_KWTShw35sDuqAMWhF7x4gg_ewfXXwQ2',
  VITE_APP_NAME: 'Biblioteca digital',
};

function findProject() {
  const candidates = [process.cwd(), __dirname,
    path.join(process.cwd(), 'repositorio-react'), path.join(__dirname, 'repositorio-react')];
  for (const root of candidates) {
    try {
      const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
      if (pkg.name === 'repositorio-academico' && pkg.scripts?.dev?.includes('vite')) return root;
    } catch {}
  }
  throw new Error('Coloca este archivo en repositorio-react, junto a package.json, y ejecutalo desde esa carpeta.');
}

function configure(root) {
  const stamp = Date.now() + '-' + process.pid;
  const wanted = new Set(Object.keys(config));
  const block = Object.entries(config).map(([key, value]) => key + '=' + value).join('\n');
  // Actualiza tambien los archivos existentes que podrian sobrescribir .env en desarrollo.
  for (const name of ['.env', '.env.local', '.env.development', '.env.development.local']) {
    const file = path.join(root, name);
    const exists = fs.existsSync(file);
    if (!exists && name !== '.env') continue;
    const old = exists ? fs.readFileSync(file, 'utf8') : '';
    const kept = old.replace(/^\uFEFF/, '').split(/\r?\n/).filter(line => {
      const key = line.split('=', 1)[0].trim().replace(/^export\s+/, '')
        .replace(/\\_/g, '_').replace(/^NEXT_PUBLIC_/, 'VITE_');
      return !wanted.has(key);
    }).join('\n').trimEnd();
    const next = (kept ? kept + '\n' : '') + block + '\n';
    if (old !== next) {
      if (exists) fs.copyFileSync(file, file + '.backup-' + stamp, fs.constants.COPYFILE_EXCL);
      fs.writeFileSync(file, next, 'utf8');
    }
    console.log('Archivo configurado: ' + name);
  }
}

async function checkConfig(root) {
  const localRequire = createRequire(path.join(root, 'package.json'));
  const { loadEnv } = await import(pathToFileURL(localRequire.resolve('vite')).href);
  // Elimina, solo de este proceso, valores antiguos que puedan ocultar los archivos.
  for (const key of Object.keys(config)) delete process.env[key];
  const loaded = loadEnv('development', root, 'VITE_');
  for (const [key, value] of Object.entries(config)) {
    if (loaded[key] !== value) throw new Error('La comprobacion de ' + key + ' fallo.');
  }
  console.log('CONFIGURACION LOCAL: CORRECTA (verificada con Vite).');
}

async function checkConnection() {
  try {
    const response = await fetch(config.VITE_SUPABASE_URL + '/auth/v1/settings', {
      headers: { apikey: config.VITE_SUPABASE_PUBLISHABLE_KEY },
      signal: AbortSignal.timeout(12000),
    });
    if (!response.ok) {
      console.log('SUPABASE: respuesta HTTP ' + response.status + '.');
      console.log('Si indica 401/403, verifica en Supabase que la URL y la clave publica pertenezcan al mismo proyecto.');
      return;
    }
    const settings = await response.json();
    console.log('CONEXION CON SUPABASE AUTH: CORRECTA.');
    console.log('GOOGLE: ' + (settings.external?.google === true
      ? 'habilitado; falta comprobar el inicio de sesion completo.'
      : 'no figura habilitado; configurar el proveedor Google en Supabase.'));
    console.log('Esta comprobacion no verifica tablas, permisos ni descarga de documentos.');
  } catch (error) {
    console.log('CONEXION REMOTA: no se pudo comprobar (' + (error.cause?.code || error.name) + ').');
    console.log('La configuracion local esta guardada. Revisa Internet y el estado/URL del proyecto Supabase.');
  }
}

async function main() {
  const root = findProject();
  if (!fs.existsSync(path.join(root, 'node_modules', 'vite'))) {
    throw new Error('Faltan dependencias. Ejecuta npm.cmd ci en la carpeta del proyecto.');
  }
  console.log('Proyecto: ' + root);
  configure(root);
  await checkConfig(root);
  await checkConnection();
  console.log('\nIniciando la pagina. Abre http://localhost:5173/ y actualiza con Ctrl+F5.');
  console.log('Deja esta terminal abierta. Para detenerla: Ctrl+C.\n');
  const child = spawn(process.platform === 'win32' ? 'npm.cmd' : 'npm', ['run', 'dev'], {
    cwd: root, stdio: 'inherit', shell: process.platform === 'win32',
    env: { ...process.env, ...config, CHOKIDAR_USEPOLLING: 'true', CHOKIDAR_INTERVAL: '500' },
  });
  child.on('error', error => { console.error(error.message); process.exitCode = 1; });
  child.on('exit', code => { process.exitCode = code || 0; });
}

module.exports = { configure, checkConfig, config };
if (require.main === module) main().catch(error => {
  console.error('ERROR: ' + error.message);
  process.exitCode = 1;
});