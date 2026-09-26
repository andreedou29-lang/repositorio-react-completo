import { useEffect, useState, type FormEvent } from 'react';
import { FileUp, FolderPlus, UserPlus, ShieldCheck } from 'lucide-react';
import {
  authorizeReader,
  revokeReader,
  listMembers,
  createFolder,
  uploadDocument,
  extensions,
  errorMessage,
} from '../lib/repository';
import type { Folder, Member } from '../types';
export default function AdminPanel({
  folders,
  onChanged,
}: {
  folders: Folder[];
  onChanged: (id?: string) => Promise<void>;
}) {
  const [tab, setTab] = useState<'documents' | 'people'>('documents');
  const [members, setMembers] = useState<Member[]>([]),
    [email, setEmail] = useState(''),
    [folder, setFolder] = useState(''),
    [name, setName] = useState(''),
    [file, setFile] = useState<File | null>(null),
    [title, setTitle] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [notice, setNotice] = useState(''),
    [inputKey, setInputKey] = useState(0);
  async function loadMembers() {
    setMembers(await listMembers());
  }
  useEffect(() => {
    void loadMembers().catch((e) => setError(errorMessage(e)));
  }, []);
  async function action(work: () => Promise<void>) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await work();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  function upload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    void action(async () => {
      const id = await uploadDocument(file, title, folder || null);
      setFile(null);
      setTitle('');
      setInputKey((x) => x + 1);
      await onChanged(id);
      setNotice('Documento guardado.');
    });
  }
  function addFolder(e: FormEvent) {
    e.preventDefault();
    void action(async () => {
      await createFolder(name);
      setName('');
      await onChanged();
      setNotice('Carpeta creada.');
    });
  }
  function authorize(e: FormEvent) {
    e.preventDefault();
    void action(async () => {
      await authorizeReader(email);
      setEmail('');
      await loadMembers();
      setNotice('Correo autorizado. Comparte la dirección del sitio con esa persona.');
    });
  }
  return (
    <section className="admin-panel">
      <div className="switcher" aria-label="Secciones de administración">
        <button aria-pressed={tab === 'documents'} onClick={() => setTab('documents')}>
          <FileUp size={17} /> Documentos
        </button>
        <button aria-pressed={tab === 'people'} onClick={() => setTab('people')}>
          <UserPlus size={17} /> Personas
        </button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="success" role="status">
          {notice}
        </p>
      )}
      {tab === 'documents' ? (
        <>
          <form onSubmit={upload} className="stack">
            <h3>Subir documento</h3>
            <label htmlFor="file">Archivo · máximo 20 MB</label>
            <input
              key={inputKey}
              id="file"
              type="file"
              accept={extensions.map((x) => '.' + x).join(',')}
              required
              disabled={busy}
              onChange={(e) => {
                const f = e.target.files?.[0] || null;
                setFile(f);
                setTitle(f?.name.replace(/\.[^.]+$/, '') || '');
              }}
            />
            <label htmlFor="title">Título</label>
            <input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              required
              disabled={busy}
            />
            <label htmlFor="folder">Carpeta</label>
            <select
              id="folder"
              value={folder}
              onChange={(e) => setFolder(e.target.value)}
              disabled={busy}
            >
              <option value="">Sin carpeta</option>
              {folders.map((f) => (
                <option value={f.id} key={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
            <button disabled={busy || !file}>{busy ? 'Guardando…' : 'Subir documento'}</button>
          </form>
          <form className="stack separated" onSubmit={addFolder}>
            <h3>
              <FolderPlus size={18} /> Crear carpeta
            </h3>
            <label htmlFor="folder-name">Nombre</label>
            <div className="inline-form">
              <input
                id="folder-name"
                value={name}
                maxLength={100}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={busy}
              />
              <button disabled={busy}>Crear</button>
            </div>
          </form>
        </>
      ) : (
        <>
          <form onSubmit={authorize} className="stack">
            <h3>Autorizar una cuenta</h3>
            <label htmlFor="reader-email">Correo de su cuenta de Google</label>
            <input
              id="reader-email"
              type="email"
              value={email}
              maxLength={254}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="persona@gmail.com"
              required
              disabled={busy}
            />
            <button disabled={busy}>
              <UserPlus size={17} /> Autorizar lector
            </button>
            <p className="hint">
              Autorizar no envía un correo. El lector ingresará con su propia cuenta de Google.
            </p>
          </form>
          <ul className="member-list">
            {members.map((m) => (
              <li key={m.email}>
                <div>
                  <strong>{m.email}</strong>
                  <span>
                    {m.role === 'admin'
                      ? 'Administrador'
                      : m.active
                        ? m.user_id
                          ? 'Lector · cuenta vinculada'
                          : 'Lector · pendiente de primer ingreso'
                        : 'Acceso revocado'}
                  </span>
                </div>
                {m.role === 'admin' ? (
                  <ShieldCheck size={20} />
                ) : (
                  <button
                    className="secondary small"
                    disabled={busy}
                    onClick={() =>
                      void action(async () => {
                        if (m.active) await revokeReader(m.email);
                        else await authorizeReader(m.email);
                        await loadMembers();
                        setNotice(m.active ? 'Acceso revocado.' : 'Acceso restablecido.');
                      })
                    }
                  >
                    {m.active ? 'Revocar' : 'Restablecer'}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
