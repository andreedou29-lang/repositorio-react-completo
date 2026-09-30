import React, { useState, useMemo } from 'react';
import { FolderOpen, FileText, ChevronLeft, Home } from 'lucide-react';
import type { Folder, DocumentRecord } from '../types';
import { presentedExtension } from '../lib/repository';

interface FolderGridProps {
  folders: Folder[];
  documents: DocumentRecord[];
  onSelectDocument: (id: string) => void;
  selectedId: string | null;
}

export default function FolderGrid({
  folders,
  documents,
  onSelectDocument,
  selectedId,
}: FolderGridProps) {
  // Ocultar "Andre" usándola como carpeta raíz interna
  const rootFolder = useMemo(() => {
    return folders.find((f) => f.name.toLowerCase() === 'andre' && f.parent_id === null) || null;
  }, [folders]);

  const initialFolderId = rootFolder ? rootFolder.id : null;
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(initialFolderId);

  // Historial de navegación / Migas de pan
  const breadcrumbs = useMemo(() => {
    const path: Folder[] = [];
    let curr = folders.find((f) => f.id === currentFolderId);
    while (curr && curr.id !== rootFolder?.id) {
      path.unshift(curr);
      curr = folders.find((f) => f.id === curr?.parent_id);
    }
    return path;
  }, [currentFolderId, folders, rootFolder]);

  // Subcarpetas del nivel actual
  const currentSubfolders = useMemo(() => {
    const targetParent = currentFolderId ?? (rootFolder ? rootFolder.id : null);
    return folders.filter((f) => f.parent_id === targetParent);
  }, [folders, currentFolderId, rootFolder]);

  // Documentos del nivel actual
  const currentDocuments = useMemo(() => {
    const targetParent = currentFolderId ?? (rootFolder ? rootFolder.id : null);
    return documents.filter((d) => d.folder_id === targetParent);
  }, [documents, currentFolderId, rootFolder]);

  const handleGoBack = () => {
    if (breadcrumbs.length > 0) {
      const parentFolder = folders.find((f) => f.id === currentFolderId);
      if (parentFolder && parentFolder.parent_id && parentFolder.parent_id !== rootFolder?.id) {
        setCurrentFolderId(parentFolder.parent_id);
      } else {
        setCurrentFolderId(initialFolderId);
      }
    }
  };

  return (
    <div className="archive-board">
      {/* Cabecera y Navegación de Migas de Pan */}
      <div className="board-header">
        <div className="breadcrumbs">
          <button
            className="breadcrumb-item"
            onClick={() => setCurrentFolderId(initialFolderId)}
          >
            <Home size={20} />
            <span>MI ARCHIVO</span>
          </button>
          {breadcrumbs.map((crumb) => (
            <React.Fragment key={crumb.id}>
              <span className="crumb-separator">/</span>
              <button
                className="breadcrumb-item active"
                onClick={() => setCurrentFolderId(crumb.id)}
              >
                {crumb.name}
              </button>
            </React.Fragment>
          ))}
        </div>

        {breadcrumbs.length > 0 && (
          <button className="back-btn" onClick={handleGoBack}>
            <ChevronLeft size={18} /> Volver
          </button>
        )}
      </div>

      {/* Rejilla de Carpetas / Semestres (Estilo Boceto) */}
      {currentSubfolders.length > 0 && (
        <div className="folder-grid">
          {currentSubfolders.map((folder) => (
            <button
              key={folder.id}
              className="folder-card"
              onClick={() => setCurrentFolderId(folder.id)}
            >
              <FolderOpen size={44} className="card-icon" />
              <span className="card-title">{folder.name}</span>
            </button>
          ))}
        </div>
      )}

      {/* Lista de Documentos en la carpeta actual */}
      {currentDocuments.length > 0 && (
        <div className="documents-section">
          <h2>Documentos disponibles</h2>
          <div className="document-grid">
            {currentDocuments.map((doc) => (
              <button
                key={doc.id}
                className={`document-card ${selectedId === doc.id ? 'selected' : ''}`}
                onClick={() => onSelectDocument(doc.id)}
              >
                <FileText size={22} />
                <div className="doc-details">
                  <span className="doc-title">{doc.title}</span>
                  <span className="doc-badge">{presentedExtension(doc).toUpperCase()}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {currentSubfolders.length === 0 && currentDocuments.length === 0 && (
        <div className="empty-board">
          <p>Esta carpeta no contiene subcarpetas ni documentos.</p>
        </div>
      )}
    </div>
  );
}
