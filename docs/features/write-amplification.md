<!-- last_verified: 2026-08-13 -->
# Feature: B2 write amplification (dashboard + per-session storage explorer)

## Purpose
Make the data fan-out of a 4D reconstruction visible: one session's source video explodes
into thousands of frames, calibration, multi-GB checkpoints, and a final splat model. This
feature shows the per-stage B2 footprint and the source → derived multiplier, per session and
across the whole bucket — the sample's headline "extreme data volume" story.

## Used By
- UI: the Dashboard (`/`) — session stat cards + write-amplification chart; the session
  detail page (`/sessions/[id]`) — the per-session **Artifacts / Storage** panel
- API: `GET /sessions/stats` (bucket-wide aggregates), `GET /sessions/{id}/storage`
  (per-session per-stage breakdown)

## Core Functions
- `service/sessions.py::get_stats` — dashboard aggregates (sessions, frames, total bytes,
  average write-amplification)
- `service/sessions.py::get_storage` — per-stage breakdown + source/derived split + multiplier
- `repo/session_store.py::storage_breakdown` — `list_objects_v2` per stage prefix

## Canonical Files
- Dashboard cards: `apps/web/src/components/dashboard/session-stats-cards.tsx`
- Dashboard chart: `apps/web/src/components/dashboard/write-amplification.tsx`
- Per-session panel: `apps/web/src/components/sessions/storage-breakdown.tsx`

## The two explorers (both kept)
- The starter's **full-bucket File Explorer** (`/files`) stays — browse/preview/download/delete
  every object in the bucket.
- This feature adds a **per-session, scoped** Artifacts / Storage view: the same B2 objects,
  but grouped by pipeline stage for one session, with counts, bytes, and the fan-out multiplier.

## Inputs
- Session manifests (for the dashboard aggregates)
- Live `list_objects_v2` per stage prefix (for the per-session breakdown)

## Outputs
- `SessionStats`: total/trained/running sessions, total frames, source/derived/total bytes,
  average write-amplification
- `SessionStorage`: per-stage `StageStorage` rows + `source_bytes`, `derived_bytes`,
  `total_bytes`, `total_objects`, `write_amplification` (derived / source — the
  source→derived fan-out multiplier)

## Canonical formula (one definition, both surfaces)
`write_amplification = derived_bytes / source_bytes` — the source→derived fan-out
multiplier. Both surfaces use it so they always agree:
- Detail card (`GET /sessions/{id}/storage` → `service/sessions.py::get_storage`) computes
  it live from the per-stage B2 listing.
- Dashboard cards + average read `metrics.write_amplification`, which the runner records in
  `service/session_runner.py::_finalize` from the same `derived / source`.

Because the detail card shows Source and Derived, `Derived ÷ Source` equals the displayed
ratio, so the figures reconcile.

## Flow
- Dashboard reads `GET /sessions/stats` and the session list, renders the stat cards and the
  source-vs-derived bar chart
- The detail page reads `GET /sessions/{id}/storage` and renders the per-stage table with the
  write-amplification multiplier. The panel refreshes live: `useSessionStorage` is driven by
  the session status and polls on the same 2s cadence as the manifest while the run is in
  progress, then refetches once when the run reaches a terminal state (the final dataset and
  preview objects are written just before the manifest flips) and stops — so the panel fills in
  without a manual reload and a finished session is not polled forever

## Edge Cases
- No runs yet → the chart and cards show an empty state (no divide-by-zero; amplification is 0)
- Source bytes 0 (pre-run) → write-amplification is 0 until a run produces derived bytes

## UX States
- Empty: "No runs yet" prompts running a session
- Loading: skeletons on cards / chart / table
- Error: inline `ErrorState` with retry

## Verification
- Test files: `services/api/tests/test_sessions.py` (`test_storage_write_amplification`,
  `test_finalize_and_storage_write_amplification_agree`)
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: storage math (derived / source, derived split, object counts) is correct,
  and `get_storage` agrees with the runner's `_finalize` on the write-amplification formula

## Related Docs
- [README.md](../../README.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Sessions](sessions.md), [File Browser](file-browser.md)
