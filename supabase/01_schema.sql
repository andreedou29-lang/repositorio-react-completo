-- Ejecutar UNA VEZ en un proyecto nuevo de Supabase, desde SQL Editor.
-- No sustituye ni modifica el repositorio publicado anteriormente.
begin;
create schema if not exists private;
revoke all on schema private from public;
grant usage on schema private to authenticated;

create table public.repository_members (
  email text primary key check (email = lower(btrim(email)) and length(email) <= 254 and email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'),
  user_id uuid unique references auth.users(id) on delete set null,
  role text not null default 'reader' check (role in ('admin','reader')),
  active boolean not null default true,
  created_at timestamptz not null default now()
);
create unique index repository_one_admin on public.repository_members(role) where role = 'admin';

create table public.folders (
  id uuid primary key default gen_random_uuid(),
  name text not null unique check (length(btrim(name)) between 1 and 100),
  created_at timestamptz not null default now()
);
create table public.documents (
  id uuid primary key,
  title text not null check (length(btrim(title)) between 1 and 200),
  original_name text not null check (length(original_name) between 1 and 200),
  folder_id uuid references public.folders(id) on delete set null,
  extension text not null check (extension in ('pdf','md','markdown','tex','bib','sty','cls','doc','docx','txt','zip','png','jpg','jpeg','webp')),
  storage_path text not null unique,
  size_bytes bigint not null check (size_bytes between 1 and 20971520),
  created_at timestamptz not null default now(),
  constraint canonical_storage_path check (storage_path = 'documents/' || id::text || '.' || extension)
);
create index documents_folder on public.documents(folder_id);
create index documents_created on public.documents(created_at desc);

alter table public.repository_members enable row level security;
alter table public.folders enable row level security;
alter table public.documents enable row level security;
revoke all on public.repository_members, public.folders, public.documents from anon, authenticated;
grant select on public.repository_members to authenticated;
grant select, insert, update, delete on public.folders, public.documents to authenticated;

-- Funciones privadas: permisos actuales en base de datos, no roles editables del navegador.
create function private.is_member() returns boolean language sql stable security definer set search_path = '' as $$
  select exists(select 1 from public.repository_members where user_id = (select auth.uid()) and active);
$$;
create function private.is_admin() returns boolean language sql stable security definer set search_path = '' as $$
  select exists(select 1 from public.repository_members where user_id = (select auth.uid()) and active and role = 'admin');
$$;
revoke all on function private.is_member(), private.is_admin() from public;
grant execute on function private.is_member(), private.is_admin() to authenticated;

create policy members_read on public.repository_members for select to authenticated
using (user_id = (select auth.uid()) or (select private.is_admin()));
create policy folders_read on public.folders for select to authenticated using ((select private.is_member()));
create policy folders_write on public.folders for all to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));
create policy documents_read on public.documents for select to authenticated using ((select private.is_member()));
create policy documents_write on public.documents for all to authenticated using ((select private.is_admin())) with check ((select private.is_admin()));

-- Solo vincula una autorización a la cuenta verificada que está iniciando sesión.
-- No acepta correo, UID ni rol enviados por el navegador.
create function public.claim_access() returns text language plpgsql security definer set search_path = '' as $$
declare caller uuid := auth.uid(); verified_email text; result_role text;
begin
  if caller is null then return null; end if;
  select lower(u.email) into verified_email from auth.users u
    where u.id = caller and u.email_confirmed_at is not null
    and exists(select 1 from auth.identities i where i.user_id = u.id and i.provider = 'google');
  if verified_email is null then return null; end if;
  update public.repository_members set user_id = caller
    where email = verified_email and active and (user_id is null or user_id = caller)
    returning role into result_role;
  return result_role;
end;
$$;

create function public.my_access() returns text language sql stable security definer set search_path = '' as $$
  select role from public.repository_members where user_id = (select auth.uid()) and active;
$$;

-- El administrador puede autorizar lectores; crear administradores exige SQL Editor.
create function public.authorize_reader(reader_email text) returns void language plpgsql security definer set search_path = '' as $$
declare normalized text := lower(btrim(reader_email));
begin
  if not private.is_admin() then raise exception 'Solo el administrador puede autorizar lectores.' using errcode = '42501'; end if;
  if normalized is null or length(normalized) > 254 or normalized !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' then
    raise exception 'Correo no válido.' using errcode = '22023';
  end if;
  if exists(select 1 from public.repository_members where email=normalized and role='admin') then
    raise exception 'Esta cuenta ya es administradora.' using errcode = '22023';
  end if;
  insert into public.repository_members(email, role) values(normalized, 'reader')
  on conflict(email) do update set active = true;
end;
$$;
create function public.revoke_reader(reader_email text) returns void language plpgsql security definer set search_path = '' as $$
begin
  if not private.is_admin() then raise exception 'Solo el administrador puede revocar permisos.' using errcode = '42501'; end if;
  update public.repository_members set active = false where email = lower(btrim(reader_email)) and role = 'reader';
end;
$$;
revoke all on function public.claim_access(), public.my_access(), public.authorize_reader(text), public.revoke_reader(text) from public;
grant execute on function public.claim_access(), public.my_access(), public.authorize_reader(text), public.revoke_reader(text) to authenticated;

-- Los lectores NO tienen SELECT directo en Storage. Descargan por la Edge Function.
-- Esto evita que puedan crear URLs firmadas reutilizables con la API de Storage.
insert into storage.buckets (id, name, public, file_size_limit)
values ('repository-files', 'repository-files', false, 20971520);
create policy repository_storage_admin_select on storage.objects for select to authenticated
using (bucket_id = 'repository-files' and (select private.is_admin()));
create policy repository_storage_admin_insert on storage.objects for insert to authenticated
with check (bucket_id = 'repository-files' and (select private.is_admin())
  and name ~ '^documents/[0-9a-f-]{36}\.(pdf|md|markdown|tex|bib|sty|cls|doc|docx|txt|zip|png|jpg|jpeg|webp)$');
create policy repository_storage_admin_delete on storage.objects for delete to authenticated
using (bucket_id = 'repository-files' and (select private.is_admin()));
commit;
