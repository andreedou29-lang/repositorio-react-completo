const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const mime = {
  pdf: 'application/pdf',
  md: 'text/plain; charset=utf-8',
  markdown: 'text/plain; charset=utf-8',
  tex: 'text/plain; charset=utf-8',
  txt: 'text/plain; charset=utf-8',
  bib: 'text/plain; charset=utf-8',
  sty: 'text/plain; charset=utf-8',
  cls: 'text/plain; charset=utf-8',
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
};

// Inyección de dependencias para probar el acceso sin exponer claves privadas.
export function createHandler({ makeUserClient, makeAdminClient, allowedOrigins }) {
  return async function handle(request) {
    const origin = request.headers.get('origin');
    const permittedOrigin = !origin || allowedOrigins.includes(origin);
    const headers = new Headers({
      'Cache-Control': 'private, no-store',
      Vary: 'Origin',
      'X-Content-Type-Options': 'nosniff',
    });
    if (origin && permittedOrigin) {
      headers.set('Access-Control-Allow-Origin', origin);
      headers.set(
        'Access-Control-Allow-Headers',
        'authorization, apikey, content-type, x-client-info',
      );
      headers.set('Access-Control-Allow-Methods', 'GET, OPTIONS');
      headers.set('Access-Control-Expose-Headers', 'Content-Disposition');
    }
    const fail = (message, status) =>
      new Response(JSON.stringify({ error: message }), {
        status,
        headers: new Headers([...headers, ['Content-Type', 'application/json']]),
      });
    if (!permittedOrigin) return fail('Origen no autorizado.', 403);
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers });
    if (request.method !== 'GET') return fail('Método no permitido.', 405);
    const authorization = request.headers.get('authorization') || '';
    if (!authorization.startsWith('Bearer ') || authorization.length > 10000)
      return fail('Inicia sesión.', 401);
    const id = new URL(request.url).searchParams.get('id') || '';
    if (!UUID.test(id)) return fail('Identificador no válido.', 400);
    try {
      const userClient = makeUserClient(authorization);
      const { data: userData, error: userError } = await userClient.auth.getUser(
        authorization.slice(7),
      );
      if (userError || !userData?.user) return fail('Sesión no válida.', 401);
      const { data: role, error: accessError } = await userClient.rpc('my_access');
      if (accessError) return fail('No se pudo comprobar el acceso.', 503);
      if (!['reader', 'admin'].includes(role)) return fail('Tu cuenta no tiene acceso.', 403);
      const { data: doc, error: docError } = await userClient
        .from('documents')
        .select('id, storage_path, extension, original_name')
        .eq('id', id)
        .maybeSingle();
      if (docError) return fail('No se pudo consultar el documento.', 503);
      if (!doc) return fail('Documento no disponible.', 404);
      // La ruta procede de una fila autorizada, nunca de un argumento del cliente.
      const { data: blob, error: downloadError } = await makeAdminClient()
        .storage.from('repository-files')
        .download(doc.storage_path);
      if (downloadError || !blob) return fail('No se pudo descargar el archivo.', 503);
      headers.set('Content-Type', mime[doc.extension] || 'application/octet-stream');
      headers.set(
        'Content-Disposition',
        `attachment; filename="documento.${doc.extension}"; filename*=UTF-8''${encodeURIComponent(doc.original_name).replace(/'/g, '%27')}`,
      );
      headers.set('Content-Security-Policy', "default-src 'none'; sandbox");
      return new Response(blob.stream(), { status: 200, headers });
    } catch (error) {
      console.error('Document download failed', error instanceof Error ? error.name : 'unknown');
      return fail('Servicio no disponible. Inténtalo de nuevo.', 503);
    }
  };
}
