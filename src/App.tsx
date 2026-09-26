import { useEffect, useState, useCallback } from 'react';
import type { Session } from '@supabase/supabase-js';
import {
  BookOpen,
  Search,
  LogOut,
  LockKeyhole,
  Menu,
  X,
  FolderOpen,
  FileText,
  Download,
  Settings,
  Trash2,
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
} from 'lucide-react';
import { appName, configured, client } from './lib/supabase';
import {
  access,
  listRepository,
  signIn,
  downloadDocument,
  deleteDocument,
  errorMessage,
  humanSize,
  presentedExtension,
  presentedSize,
} from './lib/repository';
import type { Role, Folder, DocumentRecord } from './types';
import Reader from './components/Reader';
import Modal from './components/Modal';
import AdminPanel from './components/AdminPanel';

export default function App() {
  const [session, setSession] = useState<Session | null>(null),
    [role, setRole] = useState<Role | null>(null),
    [checking, setChecking] = useState(true),
    [error, setError] = useState('');
  const [folders, setFolders] = useState<Folder[]>([]),
    [documents, setDocuments] = useState<DocumentRecord[]>([]),
    [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState(''),
    [sidebar, setSidebar] = useState(false),
    [adminOpen, setAdminOpen] = useState(false),
    [deleting, setDeleting] = useState<DocumentRecord | null>(null),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(''),
    [loading, setLoading] = useState(false),
    [retry, setRetry] = useState(0);
  const clear = useCallback(() => {
    setRole(null);
    setFolders([]);
    setDocuments([]);
    setSelectedId(null);
    setAdminOpen(false);
    setDeleting(null);
  }, []);
  useEffect(() => {
    document.title = appName;
    if (!configured) {
      setChecking(false);
      return;
    }
    let alive = true;
    client()
      .auth.getSession()
      .then(({ data, error }) => {
        if (!alive) return;
        if (error) {
          setError(error.message);
          setChecking(false);
        } else {
          setSession(data.session);
          if (!data.session) setChecking(false);
        }
      })
      .catch((e) => {
        if (alive) {
          setError(errorMessage(e));
          setChecking(false);
        }
      });
    const { data } = client().auth.onAuthStateChange((_event, next) => {
      if (alive) {
        setSession(next);
        if (!next) {
          clear();
          setChecking(false);
        }
      }
    });
    const params = new URLSearchParams(window.location.search);
    if (params.has('error_description')) {
      setError(params.get('error_description') || 'Se canceló el acceso.');
      history.replaceState(null, '', '/');
    }
    return () => {
      alive = false;
      data.subscription.unsubscribe();
    };
  }, [clear]);
  useEffect(() => {
    if (!session?.user.id) return;
    let alive = true;
    setChecking(true);
    setError('');
    access(true)
      .then((r) => {
        if (alive) setRole(r);
      })
      .catch((e) => {
        if (alive) {
          clear();
          setError(errorMessage(e));
        }
      })
      .finally(() => {
        if (alive) setChecking(false);
      });
    return () => {
      alive = false;
    };
  }, [session?.user.id, retry, clear]);
  const refresh = useCallback(async (id?: string) => {
    setLoading(true);
    try {
      const data = await listRepository();
      setFolders(data.folders);
      setDocuments(data.documents);
      setSelectedId(
        (prev) =>
          id || (data.documents.some((d) => d.id === prev) ? prev : data.documents[0]?.id || null),
      );
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    if (role) void refresh().catch((e) => setError(errorMessage(e)));
  }, [role, refresh]);
  useEffect(() => {
    if (!role) return;
    let alive = true;
    const check = () => {
      void access()
        .then((next) => {
          if (alive && !next) clear();
        })
        .catch(() => {
          /* Un error de red no modifica permisos; el servidor sigue verificando cada petición. */
        });
    };
    const interval = window.setInterval(check, 30000);
    window.addEventListener('focus', check);
    return () => {
      alive = false;
      clearInterval(interval);
      window.removeEventListener('focus', check);
    };
  }, [role, clear]);
  async function logout() {
    setBusy(true);
    setError('');
    try {
      const { error } = await client().auth.signOut({ scope: 'local' });
      if (error) throw error;
      clear();
      setSession(null);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
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
  async function download(doc: DocumentRecord) {
    setBusy(true);
    setNotice('');
    try {
      await downloadDocument(doc);
      setNotice('Descarga preparada.');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    if (!deleting) return;
    setBusy(true);
    try {
      await deleteDocument(deleting);
      setDeleting(null);
      await refresh();
      setNotice('Documento eliminado.');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  const selected = documents.find((d) => d.id === selectedId) || null;
  const selectedSize = selected ? presentedSize(selected) : null;
  const visible = documents.filter((d) =>
    `${d.title} ${d.original_name}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()),
  );
  const position = documents.findIndex((d) => d.id === selectedId);
  function choose(id: string) {
    setSelectedId(id);
    setSidebar(false);
    setNotice('');
  }
    function documentItems(folderId: string | null) {
    return visible
      .filter((d) => d.folder_id === folderId)
      .map((d) => (
        <button
          className={`document-link ${selectedId === d.id ? 'selected' : ''}`}
          key={d.id}
          aria-current={selectedId === d.id ? 'page' : undefined}
          onClick={() => choose(d.id)}
        >
          <FileText size={15} />
          <span>
            {d.title}
            <small>{presentedExtension(d).toUpperCase()}</small>
          </span>
        </button>
      ));
  }

  function folderTree(parentId: string | null, level = 0) {
    return folders
      .filter((folder) => folder.parent_id === parentId)
      .map((folder) => {
        const children = folderTree(folder.id, level + 1);
        const docs = documentItems(folder.id);

        return (
          <details open key={folder.id} className={`folder-level-${level}`}>
            <summary>
              <FolderOpen size={16} />
              <span>{folder.name}</span>
            </summary>

            <div className="folder-contents">
              {children}
              {docs}
            </div>
          </details>
        );
      });
  }

  if (!configured)
    return (
      <main className="setup">
        <BookOpen size={36} />
        <p className="eyebrow">REPOSITORIO ACADÉMICO</p>
        <h1>Configura tu biblioteca</h1>
        <p>El proyecto está listo para conectarse a tu cuenta de Supabase.</p>
        <ol>
          <li>
            Copia <code>.env.example</code> como <code>.env</code>.
          </li>
          <li>Completa la URL y la clave pública de tu proyecto.</li>
          <li>
            Sigue <code>LEEME.md</code> para configurar Google, permisos y descargas.
          </li>
          <li>
            Reinicia <code>npm run dev</code>.
          </li>
        </ol>
        <p className="hint">Los archivos privados no se cargan hasta que configures la conexión.</p>
      </main>
    );
  if (checking)
    return (
      <main className="auth-screen">
        <LoaderCircle className="spin" />
        <p>Comprobando tu acceso…</p>
      </main>
    );
  if (!session || !role)
    return (
      <main className="auth-screen">
        <div className="auth-card">
          <BookOpen size={36} />
          <p className="eyebrow">BIBLIOTECA PRIVADA</p>
          <h1>{appName}</h1>
          <p>
            {session
              ? 'Tu cuenta todavía no tiene autorización para entrar.'
              : 'Documentos y apuntes para leer, estudiar y compartir con personas autorizadas.'}
          </p>
          {session && <p className="account-email">{session.user.email}</p>}
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          {session ? (
            <>
              <button onClick={() => setRetry((x) => x + 1)} disabled={busy}>
                Comprobar autorización
              </button>
              <button className="secondary" onClick={logout} disabled={busy}>
                Salir y usar otra cuenta
              </button>
              <p className="hint">
                Pide al administrador que autorice el correo que aparece arriba.
              </p>
            </>
          ) : (
            <button onClick={login} disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={18} /> : <LockKeyhole size={18} />}{' '}
              Continuar con Google
            </button>
          )}
          <p className="auth-foot">Acceso individual · Solo cuentas autorizadas</p>
        </div>
      </main>
    );
  return (
    <div className="app-shell">
      {sidebar && (
        <button
          className="sidebar-backdrop"
          aria-label="Cerrar índice"
          onClick={() => setSidebar(false)}
        />
      )}
      <aside className={`sidebar ${sidebar ? 'open' : ''}`}>
        <header className="sidebar-brand">
          <BookOpen size={24} />
          <span>{appName}</span>
          <button
            className="icon-button mobile-only"
            aria-label="Cerrar índice"
            onClick={() => setSidebar(false)}
          >
            <X />
          </button>
        </header>
        <div className="sidebar-search">
          <Search size={17} />
          <input
            aria-label="Buscar documento"
            placeholder="Buscar un documento"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <p className="sidebar-label">
          ÍNDICE DE DOCUMENTOS <span>{documents.length}</span>
        </p>
                <nav aria-label="Índice de documentos">
          {folderTree(null)}

          {visible.some((d) => !d.folder_id) && (
            <div className="unfiled">
              <p>Sin carpeta</p>
              {documentItems(null)}
            </div>
          )}

          {!visible.length && (
            <p className="sidebar-empty">
              {query ? 'No hay coincidencias.' : 'Todavía no hay documentos.'}
            </p>
          )}
          {visible.some((d) => !d.folder_id) && (
            <div className="unfiled">
              <p>Sin carpeta</p>
              {documentItems(null)}
            </div>
          )}
          {!visible.length && (
            <p className="sidebar-empty">
              {query ? 'No hay coincidencias.' : 'Todavía no hay documentos.'}
            </p>
          )}
        </nav>
        <footer className="sidebar-footer">
          <LockKeyhole size={15} />
          <span>{role === 'admin' ? 'Administración' : 'Acceso de lectura'}</span>
        </footer>
      </aside>
      <div className="main-pane">
        <header className="topbar">
          <button
            className="icon-button mobile-only"
            aria-label="Abrir índice"
            onClick={() => setSidebar(true)}
          >
            <Menu />
          </button>
          <span className="topbar-label">
            Biblioteca /{' '}
            <strong>
              {selected?.folder_id
                ? folders.find((f) => f.id === selected.folder_id)?.name
                : 'Documentos'}
            </strong>
          </span>
          <div className="topbar-actions">
            {role === 'admin' && (
              <button className="secondary" onClick={() => setAdminOpen(true)}>
                <Settings size={16} />
                <span>Administrar</span>
              </button>
            )}
            <span className="user-email" title={session.user.email}>
              {session.user.email}
            </span>
            <button
              className="icon-button"
              onClick={logout}
              disabled={busy}
              title="Cerrar sesión"
              aria-label="Cerrar sesión"
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        {error && (
          <div className="banner error" role="alert">
            <span>{error}</span>
            <button className="icon-button" aria-label="Cerrar aviso" onClick={() => setError('')}>
              <X size={16} />
            </button>
          </div>
        )}
        {notice && (
          <p className="banner success" role="status">
            {notice}
          </p>
        )}
        <main className="reading-main">
          {loading ? (
            <div className="reader-empty" role="status">
              <LoaderCircle className="spin" />
              <p>Cargando índice…</p>
            </div>
          ) : (
            <>
              <header className="document-heading">
                <p className="eyebrow">
                  {selected
                    ? `${presentedExtension(selected).toUpperCase()}${selectedSize === null ? '' : ` · ${humanSize(selectedSize)}`}`
                    : 'TU ARCHIVO PERSONAL'}
                </p>
                <div>
                  <h1>{selected?.title || 'Bienvenido a tu biblioteca'}</h1>
                  {selected && (
                    <div className="document-actions">
                      <button
                        className="secondary"
                        onClick={() => void download(selected)}
                        disabled={busy}
                      >
                        <Download size={17} />
                        <span>{presentedExtension(selected) === 'pdf' ? 'Descargar PDF' : 'Descargar'}</span>
                      </button>
                      {role === 'admin' && (
                        <button
                          className="icon-button danger-text"
                          onClick={() => setDeleting(selected)}
                          disabled={busy}
                          title="Eliminar documento"
                          aria-label="Eliminar documento"
                        >
                          <Trash2 size={18} />
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </header>
              <Reader doc={selected} download={(d) => void download(d)} />
              {!selected && role === 'admin' && (
                <div className="empty-action">
                  <button onClick={() => setAdminOpen(true)}>Subir el primer documento</button>
                </div>
              )}
              {selected && (
                <footer className="reading-footer">
                  <button
                    className="secondary"
                    disabled={position <= 0}
                    onClick={() => choose(documents[position - 1].id)}
                  >
                    <ChevronLeft size={17} />
                    Anterior
                  </button>
                  <span>
                    {position + 1} / {documents.length}
                  </span>
                  <button
                    className="secondary"
                    disabled={position >= documents.length - 1}
                    onClick={() => choose(documents[position + 1].id)}
                  >
                    Siguiente
                    <ChevronRight size={17} />
                  </button>
                </footer>
              )}
            </>
          )}
        </main>
      </div>
      {adminOpen && role === 'admin' && (
        <Modal title="Administrar biblioteca" onClose={() => setAdminOpen(false)}>
          <AdminPanel folders={folders} onChanged={refresh} />
        </Modal>
      )}
      {deleting && (
        <Modal
          title="Eliminar documento"
          onClose={() => {
            if (!busy) setDeleting(null);
          }}
        >
          <p>
            Se eliminará «{deleting.title}» y su archivo original. Esta acción no se puede deshacer.
          </p>
          <div className="modal-actions">
            <button className="secondary" onClick={() => setDeleting(null)} disabled={busy}>
              Cancelar
            </button>
            <button className="danger" onClick={() => void remove()} disabled={busy}>
              {busy ? 'Eliminando…' : 'Eliminar documento'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
