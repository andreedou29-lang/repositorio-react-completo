// Endpoint adicional: no reemplaza serve-document ni hace publico Storage.
import { createClient } from 'npm:@supabase/supabase-js@2.116.0';

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
};
const headers = {
  ...cors,
  'Cache-Control': 'private, no-store, max-age=0',
  'X-Content-Type-Options': 'nosniff',
};
type Environment = { url: string; publicKey: string; serverKey: string };

function failure(status: number, message: string) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { ...headers, 'Content-Type': 'application/json; charset=utf-8' },
  });
}

export function createHandler(env: Environment, makeClient = createClient) {
  return async (request: Request): Promise<Response> => {
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    if (request.method !== 'GET') return failure(405, 'Método no admitido.');
    if (!env.url || !env.publicKey || !env.serverKey) {
      return failure(500, 'Falta la configuración del servidor PDF.');
    }
    const authorization = request.headers.get('Authorization') || '';
    const match = authorization.match(/^Bearer\s+(\S+)$/i);
    if (!match) return failure(401, 'Inicia sesión para leer este PDF.');
    const id = new URL(request.url).searchParams.get('id') || '';
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
      return failure(400, 'Identificador de documento inválido.');
    }
    try {
      const userClient = makeClient(env.url, env.publicKey, {
        global: { headers: { Authorization: authorization } },
        auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
      });
      // Validacion real contra Supabase Auth; no se confia en decodificar el JWT.
      const user = await userClient.auth.getUser(match[1]);
      if (user.error || !user.data.user) return failure(401, 'Tu sesión no es válida. Vuelve a iniciar sesión.');
      const role = await userClient.rpc('my_access');
      if (role.error) return failure(503, 'No se pudo comprobar el acceso al repositorio.');
      if (role.data !== 'admin' && role.data !== 'reader') {
        return failure(403, 'Tu cuenta no tiene acceso al repositorio.');
      }
      // Esta consulta utiliza el JWT del usuario: las politicas RLS siguen aplicandose.
      const record = await userClient.from('documents')
        .select('id,original_name,pdf_bucket,pdf_storage_path')
        .eq('id', id).maybeSingle();
      if (record.error) return failure(503, 'No se pudo consultar el documento.');
      const doc = record.data;
      if (!doc) return failure(404, 'Documento no disponible para esta cuenta.');
      if (!doc.pdf_storage_path) return failure(404, 'Este documento todavía no tiene un PDF generado.');
      const path = String(doc.pdf_storage_path);
      const expected = new RegExp(`^documents/${String(doc.id)}/[a-f0-9]{64}\\.pdf$`, 'i');
      if (doc.pdf_bucket !== 'repository-pdfs' || !expected.test(path)) {
        return failure(409, 'La ubicación del PDF no coincide con el documento. Repite la sincronización.');
      }
      // Cliente privilegiado separado, solo despues de autenticar y autorizar.
      // Descarga exclusivamente el objeto al que apunta la fila autorizada.
      const storageClient = makeClient(env.url, env.serverKey, {
        auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
      });
      const stored = await storageClient.storage.from('repository-pdfs').download(path);
      if (stored.error || !stored.data) return failure(502, 'No se pudo recuperar el PDF. Revisa su subida a Storage.');
      if ((await stored.data.slice(0, 5).text()) !== '%PDF-') {
        return failure(422, 'El archivo almacenado no es un PDF válido.');
      }
      const name = `${String(doc.original_name || 'documento').replace(/\.[^.]+$/, '')}.pdf`;
      const encoded = encodeURIComponent(name).replace(/['()*]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);
      return new Response(stored.data, {
        headers: {
          ...headers,
          'Content-Type': 'application/pdf',
          'Content-Disposition': `inline; filename="documento.pdf"; filename*=UTF-8''${encoded}`,
        },
      });
    } catch {
      return failure(500, 'No se pudo abrir el PDF. Revisa los registros de serve-pdf.');
    }
  };
}

function defaultKey(value: string | undefined): string {
  try {
    const keys = JSON.parse(value || '{}');
    return typeof keys.default === 'string' ? keys.default : '';
  } catch { return ''; }
}

if (typeof Deno !== 'undefined') {
  Deno.serve(createHandler({
    url: Deno.env.get('SUPABASE_URL') || '',
    publicKey: defaultKey(Deno.env.get('SUPABASE_PUBLISHABLE_KEYS')) || Deno.env.get('SUPABASE_ANON_KEY') || '',
    serverKey: defaultKey(Deno.env.get('SUPABASE_SECRET_KEYS')) || Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || '',
  }));
}
