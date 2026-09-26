import { client, publicKey, supabaseUrl } from './supabase';
import type { DocumentRecord, Folder, Member, Role } from '../types';
export const MAX_BYTES = 20 * 1024 * 1024;
export const extensions = [
  'pdf',
  'md',
  'markdown',
  'tex',
  'bib',
  'sty',
  'cls',
  'doc',
  'docx',
  'txt',
  'zip',
  'png',
  'jpg',
  'jpeg',
  'webp',
];
export const readableText = ['md', 'markdown', 'tex', 'bib', 'sty', 'cls', 'txt'];
export function hasGeneratedPdf(doc: DocumentRecord): boolean {
  return !!doc.pdf_storage_path?.trim();
}
export function presentedExtension(doc: DocumentRecord): string {
  return hasGeneratedPdf(doc) ? 'pdf' : doc.extension.toLowerCase();
}
export function presentedSize(doc: DocumentRecord): number | null {
  return hasGeneratedPdf(doc) ? (doc.pdf_size_bytes ?? null) : doc.size_bytes;
}
export function presentedFilename(doc: DocumentRecord): string {
  return hasGeneratedPdf(doc)
    ? `${doc.original_name.replace(/\.[^.]+$/, '')}.pdf`
    : doc.original_name;
}
export function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : typeof error === 'object' && error !== null && 'message' in error
      ? String(error.message)
      : 'No se pudo completar la operación.';
}
export function humanSize(n: number) {
  return n < 1024
    ? `${n} B`
    : n < 1048576
      ? `${(n / 1024).toFixed(1)} KB`
      : `${(n / 1048576).toFixed(1)} MB`;
}
export async function signIn() {
  const { error } = await client().auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: window.location.origin + '/',
      queryParams: { prompt: 'select_account' },
    },
  });
  if (error) throw error;
}
export async function access(claim = false): Promise<Role | null> {
  const { data, error } = await client().rpc(claim ? 'claim_access' : 'my_access');
  if (error) throw error;
  return data === 'admin' || data === 'reader' ? data : null;
}
export async function listRepository() {
  const [folders, documents] = await Promise.all([
    client().from('folders').select('*').order('name'),
    client().from('documents').select('*').order('created_at', { ascending: false }),
  ]);
  if (folders.error) throw folders.error;
  if (documents.error) throw documents.error;
  return { folders: folders.data as Folder[], documents: documents.data as DocumentRecord[] };
}
export async function uploadDocument(file: File, title: string, folderId: string | null) {
  const extension = file.name.split('.').pop()?.toLowerCase() || '';
  if (!extensions.includes(extension)) throw new Error('Formato no admitido.');
  if (!file.size || file.size > MAX_BYTES)
    throw new Error('El archivo debe ocupar entre 1 byte y 20 MB.');
  if (file.name.length > 200 || /[\x00-\x1f\x7f/\\]/.test(file.name))
    throw new Error('Usa un nombre de archivo más corto y sin caracteres de control.');
  if (!title.trim() || title.trim().length > 200)
    throw new Error('El título debe tener entre 1 y 200 caracteres.');
  const id = crypto.randomUUID();
  const path = `documents/${id}.${extension}`;
  const { error: storageError } = await client()
    .storage.from('repository-files')
    .upload(path, file, {
      upsert: false,
      cacheControl: '0',
      contentType: 'application/octet-stream',
    });
  if (storageError) throw storageError;
  const { error } = await client()
    .from('documents')
    .insert({
      id,
      title: title.trim(),
      folder_id: folderId || null,
      original_name: file.name,
      extension,
      storage_path: path,
      size_bytes: file.size,
    });
  if (error) {
    const cleanup = await client().storage.from('repository-files').remove([path]);
    if (cleanup.error)
      throw new Error(
        `No se guardaron los metadatos. Revisa el archivo huérfano ${path} en Storage. ${error.message}`,
      );
    throw error;
  }
  return id;
}
export async function deleteDocument(doc: DocumentRecord) {
  const stored = await client().storage.from('repository-files').remove([doc.storage_path]);
  if (stored.error) throw stored.error;
  const row = await client().from('documents').delete().eq('id', doc.id);
  if (row.error)
    throw new Error('El archivo se eliminó, pero falta eliminar su entrada. Vuelve a intentarlo.');
}
export async function createFolder(name: string) {
  if (!name.trim() || name.trim().length > 100)
    throw new Error('Escribe un nombre de entre 1 y 100 caracteres.');
  const { error } = await client().from('folders').insert({ name: name.trim() });
  if (error) throw error;
}
export async function listMembers() {
  const { data, error } = await client().from('repository_members').select('*').order('created_at');
  if (error) throw error;
  return data as Member[];
}
export async function authorizeReader(email: string) {
  const { error } = await client().rpc('authorize_reader', { reader_email: email });
  if (error) throw error;
}
export async function revokeReader(email: string) {
  const { error } = await client().rpc('revoke_reader', { reader_email: email });
  if (error) throw error;
}
export async function fetchDocument(doc: DocumentRecord, signal?: AbortSignal): Promise<Blob> {
  // La decision de acceso y la ruta real se resuelven de nuevo en el servidor.
  const endpoint = hasGeneratedPdf(doc) ? 'serve-pdf' : 'serve-document';
  const { data, error } = await client().auth.getSession();
  if (error) throw error;
  if (!data.session) throw new Error('Inicia sesión de nuevo.');
  const response = await fetch(
    `${supabaseUrl}/functions/v1/${endpoint}?id=${encodeURIComponent(doc.id)}`,
    {
      headers: { Authorization: `Bearer ${data.session.access_token}`, apikey: publicKey },
      cache: 'no-store',
      signal,
    },
  );
  if (!response.ok) {
    const failure = (await response.json().catch(() => null)) as { error?: string } | null;
    throw new Error(
      failure?.error ||
        `No se pudo descargar el archivo (${response.status}). Revisa la función ${endpoint}.`,
    );
  }
  const blob = await response.blob();
  if (presentedExtension(doc) === 'pdf') {
    if ((await blob.slice(0, 5).text()) !== '%PDF-') {
      throw new Error('El servidor no devolvió un PDF válido. Revisa la sincronización del documento.');
    }
    // Algunos originales se subieron como application/octet-stream.
    return blob.slice(0, blob.size, 'application/pdf');
  }
  return blob;
}
export async function downloadDocument(doc: DocumentRecord) {
  // Nueva comprobación de acceso en cada descarga, incluido el PDF generado.
  const blob = await fetchDocument(doc);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = presentedFilename(doc);
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
