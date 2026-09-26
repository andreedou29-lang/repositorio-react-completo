import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';

// PostgreSQL real embebido: prueba RLS y funciones SQL, sin un proyecto en la nube.
// Se simulan solo los esquemas auth/storage que aporta Supabase.
test('permisos SQL: identidad, administración, lectura, Storage y revocación', async (t) => {
  const db = new PGlite();
  const ids = {
    admin: '10000000-0000-0000-0000-000000000001',
    reader: '20000000-0000-0000-0000-000000000002',
    stranger: '30000000-0000-0000-0000-000000000003',
    unverified: '40000000-0000-0000-0000-000000000004',
    emailOnly: '50000000-0000-0000-0000-000000000005',
    document: '60000000-0000-0000-0000-000000000006',
  };
  const as = async (role, id = '') => {
    await db.exec('reset role');
    await db.query("select set_config('request.jwt.claim.sub', $1, false)", [id]);
    await db.exec('set role ' + role);
  };
  const scalar = async (sql) => Object.values((await db.query(sql)).rows[0])[0];
  try {
    await db.exec(`
      create role anon nologin; create role authenticated nologin;
      create schema auth; create schema storage;
      grant usage on schema auth, storage, public to anon, authenticated;
      create table auth.users(id uuid primary key, email text, email_confirmed_at timestamptz);
      create table auth.identities(id uuid primary key default gen_random_uuid(), user_id uuid references auth.users(id), provider text);
      create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid$$;
      create table storage.buckets(id text primary key, name text, public boolean, file_size_limit bigint);
      create table storage.objects(id uuid primary key default gen_random_uuid(), bucket_id text, name text);
      alter table storage.objects enable row level security;
      grant select, insert, update, delete on storage.objects to authenticated;
    `);
    await db.exec(await readFile(new URL('../supabase/01_schema.sql', import.meta.url), 'utf8'));
    await db.query(
      'insert into auth.users(id,email,email_confirmed_at) values($1,$2,now()),($3,$4,now()),($5,$6,now()),($7,$8,null),($9,$10,now())',
      [
        ids.admin,
        'owner@example.com',
        ids.reader,
        'reader@example.com',
        ids.stranger,
        'stranger@example.com',
        ids.unverified,
        'unverified@example.com',
        ids.emailOnly,
        'emailonly@example.com',
      ],
    );
    for (const id of [ids.admin, ids.reader, ids.stranger, ids.unverified])
      await db.query("insert into auth.identities(user_id,provider) values($1,'google')", [id]);
    await db.exec(
      "insert into public.repository_members(email,role) values('owner@example.com','admin'),('unverified@example.com','reader'),('emailonly@example.com','reader')",
    );
    await t.test('anónimo sin consultas ni funciones de autorización', async () => {
      await as('anon');
      await assert.rejects(() => db.exec('select * from public.documents'), /permission denied/);
      await assert.rejects(() => db.exec('select public.claim_access()'), /permission denied/);
    });
    await t.test('cuenta Google verificada vincula al administrador preautorizado', async () => {
      await as('authenticated', ids.admin);
      assert.equal(await scalar('select public.claim_access()'), 'admin');
      await db.exec("select public.authorize_reader(' Reader@Example.com ')");
      await db.query(
        "insert into public.documents(id,title,original_name,extension,storage_path,size_bytes) values($1,'Nota','nota.md','md',$2,12)",
        [ids.document, `documents/${ids.document}.md`],
      );
      await db.query("insert into storage.objects(bucket_id,name) values('repository-files',$1)", [
        `documents/${ids.document}.md`,
      ]);
    });
    await t.test('registro en Google no equivale a autorización', async () => {
      await as('authenticated', ids.stranger);
      assert.equal(await scalar('select public.claim_access()'), null);
      assert.equal(await scalar('select count(*) from public.documents'), 0);
      await assert.rejects(
        () => db.exec("select public.authorize_reader('stranger@example.com')"),
        /administrador/,
      );
      await assert.rejects(
        () =>
          db.exec(
            "insert into public.repository_members(email,role) values('stranger@example.com','admin')",
          ),
        /permission denied/,
      );
    });
    await t.test(
      'correo no verificado y proveedor distinto de Google no reclaman permisos',
      async () => {
        await as('authenticated', ids.unverified);
        assert.equal(await scalar('select public.claim_access()'), null);
        await as('authenticated', ids.emailOnly);
        assert.equal(await scalar('select public.claim_access()'), null);
      },
    );
    await t.test(
      'lector autorizado lee metadatos, no modifica ni accede directamente a Storage',
      async () => {
        await as('authenticated', ids.reader);
        assert.equal(await scalar('select public.claim_access()'), 'reader');
        assert.equal(await scalar('select count(*) from public.documents'), 1);
        assert.equal(await scalar('select count(*) from public.repository_members'), 1);
        assert.equal(await scalar('select count(*) from storage.objects'), 0);
        await assert.rejects(
          () => db.exec("insert into public.folders(name) values('Ataque')"),
          /row-level security/,
        );
        await assert.rejects(
          () => db.exec("select public.revoke_reader('owner@example.com')"),
          /administrador/,
        );
        await db.exec('delete from public.documents');
        assert.equal(await scalar('select count(*) from public.documents'), 1);
        await assert.rejects(
          () => db.exec("update public.repository_members set role='admin'"),
          /permission denied/,
        );
      },
    );
    await t.test(
      'revocación bloquea nuevas lecturas aunque el JWT conserve el mismo UID',
      async () => {
        await as('authenticated', ids.admin);
        await db.exec("select public.revoke_reader('reader@example.com')");
        await as('authenticated', ids.reader);
        assert.equal(await scalar('select public.my_access()'), null);
        assert.equal(await scalar('select public.claim_access()'), null);
        assert.equal(await scalar('select count(*) from public.documents'), 0);
      },
    );
    await t.test('administrador no se degrada con la función de lectores', async () => {
      await as('authenticated', ids.admin);
      await assert.rejects(
        () => db.exec("select public.authorize_reader('owner@example.com')"),
        /administradora/,
      );
      await db.exec("select public.revoke_reader('owner@example.com')");
      assert.equal(await scalar('select public.my_access()'), 'admin');
    });
    await t.test('restablecer permiso conserva la cuenta vinculada', async () => {
      await as('authenticated', ids.admin);
      await db.exec("select public.authorize_reader('reader@example.com')");
      await as('authenticated', ids.reader);
      assert.equal(await scalar('select public.my_access()'), 'reader');
    });
  } finally {
    await db.close();
  }
});
