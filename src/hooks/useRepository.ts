import { useState, useCallback } from 'react';
import { listRepository, downloadDocument, deleteDocument, errorMessage } from '../lib/repository';
import type { Folder, DocumentRecord } from '../types';

export function useRepository(setError: (msg: string) => void) {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [deleting, setDeleting] = useState<DocumentRecord | null>(null);

  const clearRepo = useCallback(() => {
    setFolders([]);
    setDocuments([]);
    setSelectedId(null);
    setDeleting(null);
  }, []);

  const refresh = useCallback(async (id?: string) => {
    setLoading(true);
    try {
      const data = await listRepository();
      setFolders(data.folders);
      setDocuments(data.documents);
      setSelectedId((prev) =>
        id || (data.documents.some((d) => d.id === prev) ? prev : data.documents[0]?.id || null)
      );
    } finally {
      setLoading(false);
    }
  }, []);

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

  return {
    folders,
    documents,
    selectedId,
    setSelectedId,
    loading,
    busy,
    notice,
    setNotice,
    deleting,
    setDeleting,
    refresh,
    download,
    remove,
    clearRepo,
  };
}
