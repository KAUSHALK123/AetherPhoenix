export type ArtifactType = 'PPTX' | 'PDF' | 'CSV' | 'DOCX' | 'IMAGE' | 'JSON' | 'CODE' | 'OTHER';

export interface ArtifactItem {
  id: string;
  filename: string;
  type: ArtifactType;
  size_bytes?: number;
  status: 'READY' | 'GENERATING' | 'FAILED';
  created_at: string;
  workflow_id?: string;
  task_id?: string;
  download_url?: string;
  preview_content?: string;
}
