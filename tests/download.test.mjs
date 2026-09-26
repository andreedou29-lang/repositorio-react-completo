import test from 'node:test';
import assert from 'node:assert/strict';
import { createHandler } from '../supabase/functions/serve-document/handler.mjs';
const id = '60000000-0000-0000-0000-000000000006';
function setup({
  user = true,
  role = 'reader',
  doc = true,
  storageError = false,
  rpcError = false,
} = {}) {
  let reads = 0;
  const handler = createHandler({
    allowedOrigins: ['http://localhost:5173'],
    makeUserClient: () => ({
      auth: {
        getUser: async () => ({ data: { user: user ? { id: 'reader-id' } : null }, error: !user }),
      },
      rpc: async () => ({ data: role, error: rpcError }),
      from: () => ({
        select: () => ({
          eq: () => ({
            maybeSingle: async () => ({
              data: doc
                ? {
                    id,
                    storage_path: `documents/${id}.md`,
                    extension: 'md',
                    original_name: 'álgebra.md',
                  }
                : null,
              error: null,
            }),
          }),
        }),
      }),
    }),
    makeAdminClient: () => ({
      storage: {
        from: () => ({
          download: async (path) => {
            reads++;
            assert.equal(path, `documents/${id}.md`);
            return {
              data: storageError ? null : new Blob(['# Álgebra\n$$x^2$$']),
              error: storageError,
            };
          },
        }),
      },
    }),
  });
  return { handler, reads: () => reads };
}
const request = (
  headers = {},
  url = `https://project.supabase.co/functions/v1/serve-document?id=${id}`,
  method = 'GET',
) =>
  new Request(url, {
    method,
    headers: { Origin: 'http://localhost:5173', Authorization: 'Bearer valid-token', ...headers },
  });
test('descarga autorizada: bytes originales, sin URL firmada y sin caché', async () => {
  const s = setup();
  const r = await s.handler(request());
  assert.equal(r.status, 200);
  assert.equal(await r.text(), '# Álgebra\n$$x^2$$');
  assert.equal(s.reads(), 1);
  assert.match(r.headers.get('Cache-Control'), /no-store/);
  assert.match(r.headers.get('Content-Disposition'), /attachment/);
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), 'http://localhost:5173');
});
test('JWT ausente o inválido no toca Storage', async () => {
  for (const [options, headers] of [
    [{}, { Authorization: '' }],
    [{ user: false }, {}],
  ]) {
    const s = setup(options);
    assert.equal((await s.handler(request(headers))).status, 401);
    assert.equal(s.reads(), 0);
  }
});
test('cuenta revocada no toca Storage', async () => {
  const s = setup({ role: null });
  assert.equal((await s.handler(request())).status, 403);
  assert.equal(s.reads(), 0);
});
test('ID sin permisos devuelve 404, no consulta el archivo', async () => {
  const s = setup({ doc: false });
  assert.equal((await s.handler(request())).status, 404);
  assert.equal(s.reads(), 0);
});
test('origen no permitido, ruta arbitraria y método incorrecto', async () => {
  const s = setup();
  assert.equal((await s.handler(request({ Origin: 'https://otra-web.test' }))).status, 403);
  assert.equal(
    (
      await s.handler(
        request({}, 'https://project.supabase.co/functions/v1/serve-document?id=../../secreto'),
      )
    ).status,
    400,
  );
  assert.equal((await s.handler(request({}, undefined, 'POST'))).status, 405);
  assert.equal(s.reads(), 0);
});
test('preflight no requiere sesión y no lee archivos', async () => {
  const s = setup();
  assert.equal((await s.handler(request({ Authorization: '' }, undefined, 'OPTIONS'))).status, 204);
  assert.equal(s.reads(), 0);
});
test('fallos de autorización/almacenamiento no se convierten en éxito', async () => {
  const a = setup({ rpcError: true });
  assert.equal((await a.handler(request())).status, 503);
  assert.equal(a.reads(), 0);
  const b = setup({ storageError: true });
  assert.equal((await b.handler(request())).status, 503);
});
