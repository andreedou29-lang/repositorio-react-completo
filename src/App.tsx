import { useEffect, useState } from 'react';
import {
  BookOpen,
  LogOut,
  LockKeyhole,
  Download,
  Settings,
  LoaderCircle,
} from 'lucide-react';

import { appName, configured } from './lib/supabase';
import { getBookSignedUrl, humanBookSize } from './lib/bookRepository';
import {
  humanSize,
  presentedExtension,
  presentedSize,
} from './lib/repository';

import Reader from './components/Reader';
import Modal from './components/Modal';
import AdminPanel from './components/AdminPanel';
import GridExplorer from './components/GridExplorer';
import BookExplorer from './components/BookExplorer';

import { useAuth } from './hooks/useAuth';
import { useRepository } from './hooks/useRepository';
import { useBookRepository } from './hooks/useBookRepository';

export default function App() {
  const {
    session,
    role,
    checking,
    busy,
    setError,
    login,
    logout,
  } = useAuth(configured);

  const {
    folders,
    documents,
    selectedId,
    setSelectedId,
    refresh,
    download,
  } = useRepository(setError);

  const {
    folders: bookFolders,
    books,
    refresh: refreshBooks,
  } = useBookRepository(setError);

  const [adminOpen, setAdminOpen] = useState(false);
  const [section, setSection] = useState<'archive' | 'books'>('archive');
  const [selectedBook, setSelectedBook] = useState<string | null>(null);

  useEffect(() => {
    document.title = appName;
  }, []);

  useEffect(() => {
    if (role) {
      void refresh().catch((e) => setError(String(e)));
      void refreshBooks();
    }
  }, [role, refresh, refreshBooks, setError]);

  const selected = documents.find((d) => d.id === selectedId) || null;
  const selectedSize = selected ? presentedSize(selected) : null;

  const currentBook = books.find((book) => book.id === selectedBook) || null;

  const [selectedBookUrl, setSelectedBookUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    if (!currentBook) {
      setSelectedBookUrl(null);
      return;
    }

    setSelectedBookUrl(null);

    void getBookSignedUrl(currentBook)
      .then((url) => {
        if (!cancelled) {
          setSelectedBookUrl(url);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setError(
            error instanceof Error
              ? error.message
              : 'No se pudo abrir el libro.'
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [currentBook, setError]);

  if (!configured) {
    return (
      <main className="setup">
        <BookOpen size={36} />
        <p className="eyebrow">REPOSITORIO ACADÉMICO</p>
        <h1>Configura tu biblioteca</h1>
      </main>
    );
  }

  if (checking) {
    return (
      <main className="auth-screen">
        <LoaderCircle className="spin" />
        <p>Comprobando tu acceso…</p>
      </main>
    );
  }

  if (!session || !role) {
    return (
      <main className="auth-screen">
        <div className="auth-card">
          <BookOpen size={36} />
          <p className="eyebrow">BIBLIOTECA PRIVADA</p>
          <h1>{appName}</h1>

          <button onClick={login} disabled={busy}>
            <LockKeyhole size={18} />
            Continuar con Google
          </button>
        </div>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <div className="main-pane">

        <header className="topbar">
          <span className="topbar-label">
            Biblioteca / <strong>{appName}</strong>
          </span>

          <div className="topbar-actions">
            {role === 'admin' && (
              <button onClick={() => setAdminOpen(true)}>
                <Settings size={16} />
                <span>Administrar</span>
              </button>
            )}

            <span className="user-email">
              {session.user.email}
            </span>

            <button onClick={logout} title="Cerrar sesión">
              <LogOut size={18} />
            </button>
          </div>
        </header>

        <div
          style={{
            display: 'flex',
            gap: '0.5rem',
            padding: '1rem 0',
            borderBottom: '1px solid #2d3949',
            marginBottom: '1.5rem',
          }}
        >
          <button
            className={section === 'archive' ? 'active' : ''}
            onClick={() => {
              setSection('archive');
              setSelectedBook(null);
            }}
          >
            ARCHIVO DIGITAL
          </button>

          <button
            className={section === 'books' ? 'active' : ''}
            onClick={() => {
              setSection('books');
              setSelectedId(null);
            }}
          >
            BIBLIOTECA DE LIBROS
          </button>
        </div>

        {section === 'archive' && (
          <>
            <GridExplorer
              folders={folders}
              documents={documents}
              selectedId={selectedId}
              onChooseDocument={(id) => setSelectedId(id)}
            />

            {selected && (
              <div className="reader-metallic-panel">
                <header
                  style={{
                    marginBottom: '1.5rem',
                    borderBottom: '1px solid #2d3949',
                    paddingBottom: '1rem',
                  }}
                >
                  <p
                    style={{
                      color: '#94a3b8',
                      fontSize: '0.8rem',
                      fontWeight: 700,
                    }}
                  >
                    {presentedExtension(selected).toUpperCase()}
                    {selectedSize !== null &&
                      ` · ${humanSize(selectedSize)}`}
                  </p>

                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <h1
                      style={{
                        color: '#ffffff',
                        fontSize: '1.6rem',
                        margin: '0.4rem 0',
                      }}
                    >
                      {selected.title}
                    </h1>

                    <button
                      className="btn-metallic-back"
                      onClick={() => void download(selected)}
                    >
                      <Download size={16} />
                      Descargar
                    </button>
                  </div>
                </header>

                <Reader
                  doc={selected}
                  download={(d) => void download(d)}
                />
              </div>
            )}
          </>
        )}

        {section === 'books' && (
          <>
            <BookExplorer
              folders={bookFolders}
              books={books}
              onChooseBook={(book) => setSelectedBook(book.id)}
            />

            {currentBook && (
              <div className="reader-metallic-panel">
                <header
                  style={{
                    marginBottom: '1.5rem',
                    borderBottom: '1px solid #2d3949',
                    paddingBottom: '1rem',
                  }}
                >
                  <p
                    style={{
                      color: '#94a3b8',
                      fontSize: '0.8rem',
                      fontWeight: 700,
                    }}
                  >
                    LIBRO · {humanSize(currentBook.size_bytes)}
                  </p>

                  <h1
                    style={{
                      color: '#ffffff',
                      fontSize: '1.6rem',
                      margin: '0.4rem 0',
                    }}
                  >
                    {currentBook.title}
                  </h1>
                </header>

                <p style={{ color: '#94a3b8' }}>
                  {currentBook.original_name}
                </p>

                <p style={{ color: '#64748b' }}>
                  {currentBook.relative_path}
                </p>

                {selectedBookUrl && (
                  <>
                    <div
                      style={{
                        marginTop: '1.5rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                      }}
                    >
                      <a
                        href={selectedBookUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-metallic-back"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          textDecoration: 'none',
                        }}
                      >
                        <BookOpen size={16} />
                        Abrir PDF en otra pestaña
                      </a>
                    </div>

                    <div
                      style={{
                        marginTop: '1.5rem',
                        width: '100%',
                        height: '80vh',
                        overflow: 'hidden',
                        borderRadius: '10px',
                        background: '#ffffff',
                        border: '1px solid #2d3949',
                      }}
                    >
                      <iframe
                        src={selectedBookUrl}
                        title={currentBook.title}
                        style={{
                          width: '100%',
                          height: '100%',
                          border: 'none',
                          display: 'block',
                        }}
                      />
                    </div>
                  </>
                )}

                {!selectedBookUrl && (
                  <p
                    style={{
                      marginTop: '1.5rem',
                      color: '#94a3b8',
                    }}
                  >
                    Cargando PDF...
                  </p>
                )}
              </div>
            )}
          </>
        )}

      </div>

      {adminOpen && role === 'admin' && (
        <Modal
          title="Administrar biblioteca"
          onClose={() => setAdminOpen(false)}
        >
          <AdminPanel
            folders={folders}
            onChanged={refresh}
          />
        </Modal>
      )}
    </div>
  );
}


