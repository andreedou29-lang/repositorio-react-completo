import { client } from './supabase';
import type { BookRecord, BookFolder } from '../types';

function normalizePath(path: string): string {
  return path.replace(/\\/g, '/');
}

export async function listBooks(): Promise<{
  folders: BookFolder[];
  books: BookRecord[];
}> {
  const { data, error } = await client()
    .from('books')
    .select('*')
    .order('relative_path');

  if (error) throw error;

  const originalBooks = (data ?? []) as BookRecord[];

  const folderMap = new Map<string, BookFolder>();
  const books: BookRecord[] = [];

  for (const originalBook of originalBooks) {
    const normalized = normalizePath(originalBook.relative_path);
    const parts = normalized
      .split('/')
      .filter((part) => part.length > 0);

    /*
     * El último elemento siempre es el archivo/libro.
     * Todo lo anterior representa carpetas.
     */
    const folderParts = parts.slice(0, -1);

    let parentId: string | null = null;

    for (const name of folderParts) {
      const key: string = parentId
        ? `${parentId}/${name}`
        : name;

      let folder = folderMap.get(key);

      if (!folder) {
        folder = {
          id: `book-folder:${key}`,
          name,
          parent_id: parentId,
        };

        folderMap.set(key, folder);
      }

      parentId = folder.id;
    }

    /*
     * IMPORTANTE:
     * El folder_id utilizado por React NO será el folder_id
     * original de Supabase.
     *
     * Será el ID virtual construido desde relative_path.
     */
    books.push({
      ...originalBook,
      folder_id: parentId,
    });
  }

  return {
    folders: Array.from(folderMap.values()),
    books,
  };
}

export function bookFolderPath(book: BookRecord): string[] {
  const normalized = normalizePath(book.relative_path);
  const parts = normalized
    .split('/')
    .filter((part) => part.length > 0);

  return parts.slice(0, -1);
}

export function humanBookSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
  return `${(bytes / 1073741824).toFixed(2)} GB`;
}

export async function getBookSignedUrl(
  book: BookRecord
): Promise<string> {
  const { data, error } = await client()
    .storage
    .from('repository-books')
    .createSignedUrl(book.storage_path, 60 * 60);

  if (error) {
    throw error;
  }

  if (!data?.signedUrl) {
    throw new Error('No se pudo generar la URL del libro.');
  }

  return data.signedUrl;
}



