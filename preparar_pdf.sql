-- Ejecutar una vez en el SQL Editor de tu proyecto Supabase.
-- Reejecutable. Mantiene los campos y registros existentes.
begin;

alter table public.documents
    add column if not exists pdf_bucket text,
    add column if not exists pdf_storage_path text,
    add column if not exists pdf_size_bytes bigint,
    add column if not exists pdf_updated_at timestamptz;

insert into storage.buckets (id, name, public, allowed_mime_types)
values ('repository-pdfs', 'repository-pdfs', false, array['application/pdf']::text[])
on conflict (id) do nothing;

do $$
begin
    if exists (select 1 from storage.buckets where id = 'repository-pdfs' and public = true) then
        raise exception 'repository-pdfs ya existe como publico. Revisa su acceso antes de continuar; esta migracion no lo cambia.';
    end if;
end
$$;

notify pgrst, 'reload schema';
commit;

-- No agrega politicas amplias de lectura ni cambia las politicas existentes.
-- El script local usa SUPABASE_SECRET_KEY. En el frontend se integraran
-- URLs firmadas y las reglas de lectura correspondientes al acceso existente.

-- Consulta de verificacion (ejecutar despues de sincronizar una nota):
-- select id, title, original_name, pdf_bucket, pdf_storage_path,
--        pdf_size_bytes, pdf_updated_at
-- from public.documents
-- where original_name = 'Class 6- 30-04-2026.md';
