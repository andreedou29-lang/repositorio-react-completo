import { useCallback, useState } from 'react';
import { listBooks } from '../lib/bookRepository';
import type { BookFolder, BookRecord } from '../types';

export function useBookRepository(setError: (msg: string) => void) {
  const [folders, setFolders] = useState<BookFolder[]>([]);
  const [books, setBooks] = useState<BookRecord[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);

    try {
      const data = await listBooks();
      setFolders(data.folders);
      setBooks(data.books);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudieron cargar los libros.');
    } finally {
      setLoading(false);
    }
  }, [setError]);

  return {
    folders,
    books,
    loading,
    refresh,
  };
}
