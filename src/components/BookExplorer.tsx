import { useState } from 'react';
import { Folder, FileText, ArrowLeft, Home, Layers } from 'lucide-react';
import type { BookFolder, BookRecord } from '../types';
import { humanBookSize } from '../lib/bookRepository';

interface BookExplorerProps {
  folders: BookFolder[];
  books: BookRecord[];
  onChooseBook: (book: BookRecord) => void;
}

export default function BookExplorer({
  folders,
  books,
  onChooseBook,
}: BookExplorerProps) {
  /*
   * La Biblioteca de Libros tiene una raíz independiente.
   * Primero se muestra únicamente LIBROS.
   * Dentro de LIBROS aparecen las carpetas reales de los libros.
   */
  const [insideLibrary, setInsideLibrary] = useState(false);
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);

  const currentFolders = folders.filter(
    (folder) => folder.parent_id === currentFolderId
  );

  const currentBooks = books.filter(
    (book) => book.folder_id === currentFolderId
  );

  const getBreadcrumbs = () => {
    const trail: BookFolder[] = [];
    let current = folders.find((folder) => folder.id === currentFolderId);

    while (current) {
      trail.unshift(current);

      const parentId = current.parent_id;

      current = folders.find(
        (folder) => folder.id === parentId
      );
    }

    return trail;
  };

  const breadcrumbs = getBreadcrumbs();

  /*
   * Pantalla inicial de la Biblioteca:
   * solamente aparece la carpeta LIBROS.
   */
  if (!insideLibrary) {
    return (
      <div className="metallic-wrapper">
        <div className="metallic-nav-bar">
          <span className="trail-item active">
            <Home size={14} style={{ marginRight: '6px' }} />
            BIBLIOTECA DE LIBROS
          </span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <h3 className="section-title-metallic">
            <Layers
              size={18}
              style={{ display: 'inline', marginRight: '8px' }}
            />
            Biblioteca
          </h3>

          <div className="grid-3x3">
            <button
              className="card-metallic"
              onClick={() => setInsideLibrary(true)}
            >
              <div className="icon-box-metallic">
                <Folder size={28} />
              </div>

              <span className="title-metallic">
                LIBROS
              </span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="metallic-wrapper">
      <div className="metallic-nav-bar">
        <button
          className="btn-metallic-back"
          onClick={() => {
            if (currentFolderId !== null) {
              const current = folders.find(
                (folder) => folder.id === currentFolderId
              );

              setCurrentFolderId(current?.parent_id ?? null);
            } else {
              setInsideLibrary(false);
            }
          }}
        >
          <ArrowLeft size={16} />
          Volver
        </button>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            flexWrap: 'wrap',
          }}
        >
          <span
            className={`trail-item ${
              currentFolderId === null ? 'active' : ''
            }`}
            onClick={() => setCurrentFolderId(null)}
          >
            <Home size={14} style={{ marginRight: '6px' }} />
            LIBROS
          </span>

          {breadcrumbs.map((folder) => (
            <span
              key={folder.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <span style={{ color: '#4a5a70' }}>›</span>

              <span
                className={`trail-item ${
                  currentFolderId === folder.id ? 'active' : ''
                }`}
                onClick={() => setCurrentFolderId(folder.id)}
              >
                {folder.name}
              </span>
            </span>
          ))}
        </div>
      </div>

      {currentFolders.length > 0 && (
        <div style={{ marginBottom: '2.5rem' }}>
          <h3 className="section-title-metallic">
            <Layers
              size={18}
              style={{ display: 'inline', marginRight: '8px' }}
            />
            Carpetas
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

                <span className="title-metallic">
                  {folder.name}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {currentBooks.length > 0 && (
        <div style={{ marginBottom: '2.5rem' }}>
          <h3 className="section-title-metallic">
            <FileText
              size={18}
              style={{ display: 'inline', marginRight: '8px' }}
            />
            Libros
          </h3>

          <div className="grid-3x3">
            {currentBooks.map((book) => (
              <button
                key={book.id}
                className="card-metallic"
                onClick={() => onChooseBook(book)}
              >
                <div className="icon-box-metallic">
                  <FileText size={26} />
                </div>

                <span className="title-metallic">
                  {book.title}
                </span>

                <span className="badge-metallic">
                  {humanBookSize(book.size_bytes)}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {!currentFolders.length && !currentBooks.length && (
        <div
          style={{
            textAlign: 'center',
            padding: '3rem',
            color: '#64748b',
          }}
        >
          <p>Esta carpeta no contiene libros ni subcarpetas.</p>
        </div>
      )}
    </div>
  );
}
