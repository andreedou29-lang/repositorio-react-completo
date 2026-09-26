import { createClient } from 'npm:@supabase/supabase-js@2.116.0';
import { createHandler } from './handler.mjs';
const url = Deno.env.get('SUPABASE_URL')!;
const anonKey = Deno.env.get('SUPABASE_ANON_KEY')!;
// Disponible únicamente dentro de Supabase Edge Functions; jamás va en VITE_*.
const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const allowedOrigins = (Deno.env.get('ALLOWED_ORIGINS') || '')
  .split(',')
  .map((x) => x.trim())
  .filter(Boolean);
Deno.serve(
  createHandler({
    allowedOrigins,
    makeUserClient: (authorization: string) =>
      createClient(url, anonKey, {
        global: { headers: { Authorization: authorization } },
        auth: { persistSession: false, autoRefreshToken: false },
      }),
    makeAdminClient: () =>
      createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } }),
  }),
);
