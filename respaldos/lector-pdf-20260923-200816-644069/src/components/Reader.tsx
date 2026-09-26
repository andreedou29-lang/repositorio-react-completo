import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { BookOpen, Download, FileText, LoaderCircle } from 'lucide-react';
import { fetchDocument, readableText, errorMessage, presentedExtension, presentedSize } from '../lib/repository';
import type { DocumentRecord } from '../types';
export default function Reader({
  doc,
  download,
}: {
  doc: DocumentRecord | null;
  download: (doc: DocumentRecord) => void;
}) {
  const extension = doc ? presentedExtension(doc) : '';
  const resourceKey = doc ? JSON.stringify([
    doc.id, doc.storage_path, doc.extension, doc.size_bytes,
    doc.pdf_bucket, doc.pdf_storage_path, doc.pdf_size_bytes, doc.pdf_updated_at,
  ]) : '';
  const [state, setState] = useState({ key: '', text: '', url: '', loading: false, error: '' });
  const [retry, setRetry] = useState(0);
  // Evita mostrar durante un render el PDF anterior al cambiar de documento.
  const { text, url, loading, error } = state.key === resourceKey
    ? state
    : { text: '', url: '', loading: !!doc, error: '' };
  useEffect(() => {
    const abort = new AbortController();
    let objectUrl = '';
    const empty = { key: resourceKey, text: '', url: '', loading: false, error: '' };
    setState(empty);
    if (!doc) return () => abort.abort();
    const supported =
      readableText.includes(extension) ||
      ['pdf', 'png', 'jpg', 'jpeg', 'webp'].includes(extension);
    if (!supported) return () => abort.abort();
    if (readableText.includes(extension) && (presentedSize(doc) ?? 0) > 2 * 1024 * 1024) {
      setState({ ...empty, error: 'Este texto supera el límite de vista previa (2 MB). Puedes descargarlo.' });
      return () => abort.abort();
    }
    setState({ ...empty, loading: true });
    fetchDocument(doc, abort.signal)
      .then(async (blob) => {
        if (abort.signal.aborted) return;
        if (readableText.includes(extension)) {
          const value = await blob.text();
          if (!abort.signal.aborted) setState({ ...empty, text: value });
        } else {
          objectUrl = URL.createObjectURL(blob);
          setState({ ...empty, url: objectUrl });
        }
      })
      .catch((e) => {
        if (!abort.signal.aborted) setState({ ...empty, error: errorMessage(e) });
      });
    return () => {
      abort.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [resourceKey, retry]);
  if (!doc)
    return (
      <div className="reader-empty">
        <BookOpen size={46} />
        <h2>Tu biblioteca, abierta a las ideas.</h2>
        <p>Selecciona un documento del índice para empezar a leer.</p>
      </div>
    );
  if (loading)
    return (
      <div className="reader-empty" role="status">
        <LoaderCircle className="spin" />
        <p>Abriendo documento…</p>
      </div>
    );
  if (error)
    return (
      <div className="reader-empty" role="alert">
        <p>{error}</p>
        <button onClick={() => setRetry((x) => x + 1)}>Reintentar</button>
      </div>
    );
  if (extension === 'pdf')
    return url ? (
      <section className="pdf-viewer" aria-label={`PDF: ${doc.title}`}>
        <div className="pdf-toolbar">
          <span>Versión PDF</span>
          <a className="secondary" href={url} target="_blank" rel="noopener noreferrer">
            Abrir en otra pestaña
          </a>
        </div>
        <iframe className="pdf-reader" title={doc.title} src={url} />
        <p className="pdf-help">Si el visor no aparece, abre el PDF en otra pestaña o utiliza Descargar PDF.</p>
      </section>
    ) : null;
  if (['png', 'jpg', 'jpeg', 'webp'].includes(extension))
    return url ? <img className="image-reader" src={url} alt={doc.title} /> : null;
  if (['md', 'markdown'].includes(extension))
    return (
      <article className="markdown">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[[rehypeKatex, { strict: 'ignore', trust: false, throwOnError: false }]]}
          skipHtml
          components={{
            a: ({ children, href }) => (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            ),
            img: ({ alt }) => (
              <span className="attachment-note">[Imagen adjunta: {alt || 'sin descripción'}]</span>
            ),
          }}
        >
          {text}
        </ReactMarkdown>
      </article>
    );
  if (readableText.includes(extension)) return <pre className="source-reader">{text}</pre>;
  return (
    <div className="reader-empty">
      <FileText size={44} />
      <h2>Archivo original</h2>
      <p>Descarga este documento para abrirlo en tu computadora.</p>
      <button onClick={() => download(doc)}>
        <Download size={17} /> Descargar {doc.extension.toUpperCase()}
      </button>
    </div>
  );
}
