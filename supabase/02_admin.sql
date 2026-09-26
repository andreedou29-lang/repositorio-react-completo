-- Cambia el correo ANTES de ejecutar este archivo en SQL Editor.
-- Debe ser exactamente el correo de tu cuenta de Google.
do $$
declare owner_email text := 'CAMBIA_ESTO_POR_TU_CORREO@gmail.com';
begin
  if owner_email like 'CAMBIA_ESTO%' then
    raise exception 'Primero reemplaza el correo de ejemplo por tu cuenta de Google.';
  end if;
  insert into public.repository_members(email, role, active)
    values (lower(btrim(owner_email)), 'admin', true);
end;
$$;
