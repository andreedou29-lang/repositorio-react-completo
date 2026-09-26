export type Role = 'admin' | 'reader';
export interface Folder {
  id: string;
  name: string;
  created_at: string;
}
export interface DocumentRecord {
  id: string;
  title: string;
  original_name: string;
  folder_id: string | null;
  extension: string;
  storage_path: string;
  size_bytes: number;
  created_at: string;
  pdf_bucket?: string | null;
  pdf_storage_path?: string | null;
  pdf_size_bytes?: number | null;
  pdf_updated_at?: string | null;
}
export interface Member {
  email: string;
  user_id: string | null;
  role: Role;
  active: boolean;
  created_at: string;
}
