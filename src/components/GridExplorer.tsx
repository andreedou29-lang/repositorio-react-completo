import React, { useState, useEffect } from 'react';
import { Folder, FileText, ChevronRight, ArrowLeft, Home, Layers } from 'lucide-react';
import { presentedExtension } from '../lib/repository';
import type { Folder as FolderType, DocumentRecord } from '../types';

interface GridExplorerProps {
  folders: FolderType[];
  documents: DocumentRecord[];
  selectedId: string | null;
  onChooseDocument: (id: string) => void;
}

export default function GridExplorer({
  folders,
  documents,
  selectedId,
  onChooseDocument,
}: GridExplorerProps) {
  const rootFolder = folders.find((f) => f.name.toLowerCase() === 'andre');
  const rootId = rootFolder ? rootFolder.id : null;

  const [currentFolderId, setCurrentFolderId] = useState<string | null>(rootId);

  useEffect(() => {
    if (rootId && currentFolderId === null) {
      setCurrentFolderId(rootId);
    }
  }, [rootId, currentFolderId]);

  const getBreadcrumbs = () => {
    const trail: FolderType[] = [];
    let current = folders.find((f) => f.id === currentFolderId);
    while (current && current.id !== rootId) {
      trail.unshift(current);
      const parentId = current.parent_id;
      current = folders.find((f) => f.id === parentId);
    }
    return trail;
  };

  const breadcrumbs = getBreadcrumbs();
  const currentFolders = folders.filter((f) => f.parent_id === currentFolderId && f.name.toLowerCase() !== 'imagenes');
  const currentDocs = documents.filter((d) => d.folder_id === currentFolderId);

  return (
    <div className="metallic-wrapper">
      {/* Barra de Navegación */}
      <div className="metallic-nav-bar">
        {currentFolderId !== rootId && (
          <button
            className="btn-metallic-back"
            onClick={() => {
              const current = folders.find((f) => f.id === currentFolderId);
              setCurrentFolderId(current?.parent_id || rootId);
            }}
          >
            <ArrowLeft size={16} /> Volver
          </button>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span
            className={`trail-item ${currentFolderId === rootId ? 'active' : ''}`}
            onClick={() => setCurrentFolderId(rootId)}
          >
            <Home size={14} style={{ marginRight: '6px' }} />
            MI ARCHIVO
          </span>
          {breadcrumbs.map((b) => (
            <React.Fragment key={b.id}>
              <ChevronRight size={14} style={{ color: '#4a5a70' }} />
              <span
                className={`trail-item ${currentFolderId === b.id ? 'active' : ''}`}
                onClick={() => setCurrentFolderId(b.id)}
              >
                {b.name}
              </span>
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Secciones en retícula 3x3 */}
      {currentFolders.length > 0 && (
        <div style={{ marginBottom: '2.5rem' }}>
          <h3 className="section-title-metallic">
            <Layers size={18} style={{ display: 'inline', marginRight: '8px' }} />
            Carpetas / Semestres
          </h3>
          <div className="grid-3x3">
            {currentFolders.map((folder) => (
              <button
                key={folder.id}
                className="card-metallic"
                onClick={() => setCurrentFolderId(folder.id)}
              >
                <div className="icon-box-metallic">
                  <Folder size={28} />
                </div>
                <span className="title-metallic">{folder.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {currentDocs.length > 0 && (
        <div style={{ marginBottom: '2.5rem' }}>
          <h3 className="section-title-metallic">
            <FileText size={18} style={{ display: 'inline', marginRight: '8px' }} />
            Documentos Disponibles
          </h3>
          <div className="grid-3x3">
            {currentDocs.map((doc) => (
              <button
                key={doc.id}
                className={`card-metallic ${selectedId === doc.id ? 'selected-doc' : ''}`}
                onClick={() => onChooseDocument(doc.id)}
              >
                <div className="icon-box-metallic">
                  <FileText size={26} />
                </div>
                <span className="title-metallic">{doc.title}</span>
                <span className="badge-metallic">{presentedExtension(doc).toUpperCase()}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {!currentFolders.length && !currentDocs.length && (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
          <p>Esta carpeta no contiene archivos ni subcarpetas.</p>
        </div>
      )}
    </div>
  );
}


