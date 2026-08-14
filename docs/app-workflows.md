<!-- last_verified: 2026-08-13 -->
# App Workflows

User journeys inside the application. The primary entity is a **Session** (a 4D
volumetric capture); its record is a JSON manifest in B2, so every journey below is
backed by object storage, not a database.

## Create a Session

- User navigates to `/sessions/new`
- Fills the capture parameters. Finite-option fields are **selectors** (never free text):
  scene preset (`orbit-dancer` | `bouncing-prims` | `rotating-bust`), number of cameras
  (`4 | 8 | 12 | 20`), frames per camera (`12 | 24 | 48`), and training quality
  (`draft | balanced | high`). Safe fast defaults are surfaced as field descriptions
  (never an autofill button): `orbit-dancer`, 4 cameras, 12 frames, `draft`
- Submitting writes a `draft` `sessions/<id>/manifest.json` to B2 and routes to the detail page
- See: [Sessions](features/sessions.md)

## Browse Sessions

- User navigates to `/sessions`
- A grid of session cards shows name, scene preset, camera/frame counts, status, and
  (once run) the write-amplification ratio
- Empty state prompts creating the first session
- See: [Sessions](features/sessions.md)

## Run a Session

- On the detail page (`/sessions/[id]`) the user clicks **Run**
- The API marks the session `running` and returns immediately (the pipeline runs on a
  background thread); the page polls the manifest every 2s so the stage timeline advances
  **live** — no manual reload — with an overall determinate progress bar (settled stages /
  total)
- Stages: ingest → extract → calibrate → stage → train → export. The CPU stages run for
  real (synthetic footage is generated if no source video was ingested); the CUDA-only
  train/export tail auto-gates on a non-CUDA host and is marked "skipped (CUDA required)"
- The detail page shows the multi-view preview, the stage timeline, 4D metrics, the exact
  4DGaussians `train.py` command, and the per-session storage breakdown
- A session is re-runnable
- See: [Multi-view ingest](features/multiview-ingest.md), [4D training](features/fourd-training.md)

## Edit a Session

- User navigates to `/sessions/[id]/edit` (or clicks **Edit** on the detail page)
- The form opens pre-filled from the real manifest; tunable params + name can change while
  the session is `draft` or `ready`
- Once a session has run, its parameters are **locked** — the edit page shows a clear
  "parameters are locked" notice with a link back, and the API rejects the PATCH with a 409
- See: [Sessions](features/sessions.md)

## Delete a Session

- On the detail page the user clicks **Delete** and confirms
- The API removes the manifest **and every B2 object under the session's prefixes**
  (source video, frames, calibration, dataset, checkpoints, model, preview) — strictly
  scoped to that one session id, so no other session's or app's data is ever touched
- See: [Sessions](features/sessions.md)

## Inspect per-session storage (write amplification)

- The detail page's **Artifacts / Storage** panel lists each pipeline stage with its object
  count and bytes, plus the source → derived fan-out and the write-amplification multiplier
- The dashboard aggregates this across every session
- See: [Write amplification](features/write-amplification.md)

## Upload source video (full-bucket Upload, kept)

- User navigates to `/upload`
- Drops or selects files in the dropzone; the client validates size (max 100MB) and type
- Files upload **directly from the browser to B2** (a presigned PUT) with a determinate
  progress bar, then an indeterminate "Verifying upload..." phase while the API inspects the
  stored object
- The queue lives in an app-wide provider, so navigating away keeps the upload running
- See: [File Upload](features/file-upload.md)

## Browse and Manage the Bucket (full-bucket Explorer, kept)

- User navigates to `/files`
- The page loads the 100 most recent objects (most recent first); a long cold listing is
  narrated on screen. Files show in a tree view with type-specific icons
- Clicking a file opens a preview dialog (image/PDF) with a metadata panel and
  download/delete actions; the per-row menu is always visible
- Delete holds its confirmation dialog through the in-flight request, then the row disappears
  optimistically and the list reconciles with the server
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- Session stat cards show total sessions, frames extracted, total B2 footprint, and average
  write-amplification — all read from the session manifests
- A **write-amplification** chart plots source vs. derived bytes per session
- A recent-sessions panel links straight into each session's detail page
- Empty state prompts creating the first session
- See: [Write amplification](features/write-amplification.md)

## Change Preferences

- User navigates to `/settings`
- A banner states the page is mostly a demonstration: only Theme is wired up for real
- **Theme** (real): editing and saving applies it immediately and persists it (`next-themes`);
  the header's theme toggle drives the same state
- **Profile and preference fields** (demo): labelled "Demo field", persist to `localStorage`
  only, and drive no behaviour — there is no account system behind them
- Danger Zone actions are a demo — no real delete runs
- See: [Settings](features/settings.md)
