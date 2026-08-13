export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- 4D volumetric capture Sessions ----------------------------------------

export type ScenePreset = "orbit-dancer" | "bouncing-prims" | "rotating-bust";
export type NumCameras = 4 | 8 | 12 | 20;
export type FramesPerCamera = 12 | 24 | 48;
export type Quality = "draft" | "balanced" | "high";
export type SessionStatus =
  | "draft"
  | "ready"
  | "running"
  | "done"
  | "failed";
export type StageName =
  | "ingest"
  | "extract"
  | "calibrate"
  | "stage"
  | "train"
  | "export";
export type StageStatus =
  | "pending"
  | "running"
  | "done"
  | "skipped"
  | "failed";
export type ArtifactKind =
  | "video"
  | "frames"
  | "calibration"
  | "init_cloud"
  | "checkpoint"
  | "model"
  | "manifest"
  | "preview"
  | "dataset";

export interface SessionStage {
  name: StageName;
  status: StageStatus;
  message: string;
  object_count: number;
  bytes: number;
  started_at: string | null;
  finished_at: string | null;
}

export interface SessionArtifact {
  kind: ArtifactKind;
  key: string;
  bytes: number;
  object_count: number;
  content_type: string;
  version_id: string | null;
}

export interface SessionMetrics {
  num_cameras: number;
  frames_per_camera: number;
  total_frames: number;
  duration_seconds: number;
  init_points: number;
  model_points: number;
  source_bytes: number;
  frame_bytes: number;
  checkpoint_bytes: number;
  model_bytes: number;
  write_amplification: number;
  device: string;
  trained: boolean;
}

export interface SessionParams {
  scene_preset: ScenePreset;
  num_cameras: NumCameras;
  frames_per_camera: FramesPerCamera;
  quality: Quality;
}

export interface Session {
  id: string;
  name: string;
  status: SessionStatus;
  params: SessionParams;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
  stages: SessionStage[];
  artifacts: SessionArtifact[];
  metrics: SessionMetrics;
  preview_key: string | null;
  train_command: string;
  error: string | null;
}

export interface SessionCreate extends SessionParams {
  name: string;
}

export interface SessionUpdate {
  name?: string;
  scene_preset?: ScenePreset;
  num_cameras?: NumCameras;
  frames_per_camera?: FramesPerCamera;
  quality?: Quality;
}

export interface StageStorage {
  stage: string;
  prefix: string;
  object_count: number;
  bytes: number;
  bytes_human: string;
}

export interface SessionStorage {
  session_id: string;
  stages: StageStorage[];
  source_bytes: number;
  derived_bytes: number;
  total_bytes: number;
  total_objects: number;
  write_amplification: number;
}

export interface SessionStats {
  total_sessions: number;
  trained_sessions: number;
  running_sessions: number;
  total_frames: number;
  total_source_bytes: number;
  total_derived_bytes: number;
  total_bytes: number;
  total_bytes_human: string;
  avg_write_amplification: number;
}
