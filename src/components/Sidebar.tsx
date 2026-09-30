import React from 'react';
import { BookOpen, Search, X, FolderOpen, FileText, LockKeyhole } from 'lucide-react';
import { appName } from '../lib/supabase';
import { presentedExtension } from '../lib/repository';
import type { Folder, DocumentRecord, Role } from '../types';

interface SidebarProps {
  sidebar: boolean;
  setSidebar: (open: boolean) => void;
  query: string;
  setQuery: (query: string) => void;
  documents: DocumentRecord[];
  folders: Folder[];
  selectedId: string | null;
  onChoose: (id: string) => void;
  role: Role | null;
}

export default function Sidebar({
  sidebar,
  setSidebar,
  query,
  setQuery,
  documents,
  folders,
  selectedId,
  onChoose,
  role,
}: SidebarProps) {
  const visible = documents.filter((d) =>
    `${d.title} ${d.original_name}`.toLocaleLowerCase().includes(query.toLocaleLowerCase())
  );

  function documentItems(folderId: string | null) {
    return visible
      .filter((d) => d.folder_id === folderId)
      .map((d) => (
        <button
          className={`document-link ${selectedId === d.id ? 'selected' : ''}`}
          key={d.id}
          aria-current={selectedId === d.id ? 'page' : undefined}
          onClick={() => onChoose(d.id)}
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
          /* Sin el atributo 'open': todas las carpetas inician cerradas/comprimidas */
          <details key={folder.id} className={`folder-level-${level}`}>
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

  return (
    <>
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
        </nav>
        <footer className="sidebar-footer">
          <LockKeyhole size={15} />
          <span>{role === 'admin' ? 'Administración' : 'Acceso de lectura'}</span>
        </footer>
      </aside>
    </>
  );
}
