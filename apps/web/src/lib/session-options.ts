import type {
  FramesPerCamera,
  NumCameras,
  Quality,
  ScenePreset,
  SessionStatus,
  StageStatus,
} from "@4d-gaussian-splatting-volumetric-capture/shared";

// Finite option sets — mirror the backend Literals so the selectors and the API
// boundary always agree. Rendered as Selects on both the create and edit forms.
export const SCENE_PRESETS: { value: ScenePreset; label: string; hint: string }[] = [
  { value: "orbit-dancer", label: "Orbit dancer", hint: "A subject rotating over time" },
  { value: "bouncing-prims", label: "Bouncing prims", hint: "Primitives bouncing in place" },
  { value: "rotating-bust", label: "Rotating bust", hint: "A slow-rotating bust" },
];

export const NUM_CAMERAS_OPTIONS: NumCameras[] = [4, 8, 12, 20];
export const FRAMES_PER_CAMERA_OPTIONS: FramesPerCamera[] = [12, 24, 48];

export const QUALITY_OPTIONS: { value: Quality; label: string; hint: string }[] = [
  { value: "draft", label: "Draft", hint: "Fast: ~3k iterations, small resolution" },
  { value: "balanced", label: "Balanced", hint: "~14k iterations, medium resolution" },
  { value: "high", label: "High", hint: "~30k iterations, larger resolution" },
];

// Safe, fast create-form defaults (surfaced as guidance, never auto-filled).
export const CREATE_DEFAULTS = {
  scene_preset: "orbit-dancer" as ScenePreset,
  num_cameras: 4 as NumCameras,
  frames_per_camera: 12 as FramesPerCamera,
  quality: "draft" as Quality,
};

export function scenePresetLabel(value: string): string {
  return SCENE_PRESETS.find((p) => p.value === value)?.label ?? value;
}

export const STATUS_STYLES: Record<SessionStatus, { label: string; dot: string }> = {
  draft: { label: "Draft", dot: "bg-muted-foreground" },
  ready: { label: "Ready", dot: "bg-[var(--brand-b2)]" },
  running: { label: "Running", dot: "bg-[var(--warning)]" },
  done: { label: "Done", dot: "bg-[var(--success)]" },
  failed: { label: "Failed", dot: "bg-destructive" },
};

export const STAGE_LABELS: Record<string, string> = {
  ingest: "Ingest",
  extract: "Extract frames",
  calibrate: "Calibrate",
  stage: "Stage dataset",
  train: "Train (CUDA)",
  export: "Export (CUDA)",
};

export const STAGE_STATUS_DOT: Record<StageStatus, string> = {
  pending: "bg-muted-foreground/40",
  running: "bg-[var(--warning)] animate-pulse",
  done: "bg-[var(--success)]",
  skipped: "bg-[var(--brand-b2)]",
  failed: "bg-destructive",
};
