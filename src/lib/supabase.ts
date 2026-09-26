import { createClient } from '@supabase/supabase-js';
export const supabaseUrl = (import.meta.env.VITE_SUPABASE_URL || '').trim().replace(/\/$/, '');
export const publicKey = (import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || '').trim();
export const appName = import.meta.env.VITE_APP_NAME || 'Biblioteca de Andre Edou';
export const configured =
  /^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(supabaseUrl) &&
  !!publicKey &&
  !publicKey.includes('TU_CLAVE');
// Esta clave es pública. La autorización reside en RLS y en la Edge Function.
// Nunca pegar aquí una clave secret/service_role ni un secreto de Google.
export const supabase = configured
  ? createClient(supabaseUrl, publicKey, {
      auth: {
        flowType: 'pkce',
        detectSessionInUrl: true,
        persistSession: true,
        autoRefreshToken: true,
      },
    })
  : null;
export function client() {
  if (!supabase) throw new Error('Configura .env y reinicia npm run dev.');
  return supabase;
}
