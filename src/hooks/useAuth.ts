import { useState, useEffect, useCallback } from 'react';
import type { Session } from '@supabase/supabase-js';
import { client } from '../lib/supabase';
import { access, signIn, errorMessage } from '../lib/repository';
import type { Role } from '../types';

export function useAuth(configured: boolean) {
  const [session, setSession] = useState<Session | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);

  const clearAuth = useCallback(() => {
    setRole(null);
  }, []);

  useEffect(() => {
    if (!configured) {
      setChecking(false);
      return;
    }
    let alive = true;
    
    client().auth.getSession().then(({ data, error }) => {
      if (!alive) return;
      if (error) {
        setError(error.message);
        setChecking(false);
      } else {
        setSession(data.session);
        if (!data.session) setChecking(false);
      }
    }).catch(e => {
      if (alive) {
        setError(errorMessage(e));
        setChecking(false);
      }
    });

    const { data } = client().auth.onAuthStateChange((_event, next) => {
      if (alive) {
        setSession(next);
        if (!next) {
          clearAuth();
          setChecking(false);
        }
      }
    });

    const params = new URLSearchParams(window.location.search);
    if (params.has('error_description')) {
      setError(params.get('error_description') || 'Se canceló el acceso.');
      window.history.replaceState(null, '', '/');
    }

    return () => {
      alive = false;
      data.subscription.unsubscribe();
    };
  }, [configured, clearAuth]);

  useEffect(() => {
    if (!session?.user.id) return;
    let alive = true;
    setChecking(true);
    setError('');
    
    access(true).then((r) => {
      if (alive) setRole(r);
    }).catch((e) => {
      if (alive) {
        clearAuth();
        setError(errorMessage(e));
      }
    }).finally(() => {
      if (alive) setChecking(false);
    });

    return () => { alive = false; };
  }, [session?.user.id, retry, clearAuth]);

  useEffect(() => {
    if (!role) return;
    let alive = true;
    const check = () => {
      void access().then((next) => {
        if (alive && !next) clearAuth();
      }).catch(() => {});
    };
    const interval = window.setInterval(check, 30000);
    window.addEventListener('focus', check);
    return () => {
      alive = false;
      clearInterval(interval);
      window.removeEventListener('focus', check);
    };
  }, [role, clearAuth]);

  async function login() {
    setBusy(true);
    setError('');
    try {
      await signIn();
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    setError('');
    try {
      const { error } = await client().auth.signOut({ scope: 'local' });
      if (error) throw error;
      clearAuth();
      setSession(null);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const triggerRetry = () => setRetry(x => x + 1);

  return {
    session,
    role,
    checking,
    error,
    busy,
    setError,
    login,
    logout,
    triggerRetry,
    clearAuth
  };
}
