<!-- last_verified: 2026-08-13 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance overview of the 4D volumetric capture pipeline: how many sessions
exist, how much has been reconstructed, the total B2 footprint, and the write-amplification
fan-out from source video to derived artifacts. (This is the one screen the starter kit is
designed to be rewritten per app; here it is re-aimed at Sessions.)

## Used By
- UI: `/` (dashboard home)
- API: `GET /sessions/stats`, `GET /sessions`

## Core Functions
- `apps/web/src/components/dashboard/session-stats-cards.tsx` — session stat cards
  (total sessions, frames extracted, total B2 footprint, average write-amplification)
- `apps/web/src/components/dashboard/write-amplification.tsx` — source-vs-derived bar chart per session
- `apps/web/src/components/sessions/session-card.tsx` — reused for the recent-sessions panel
- `apps/web/src/lib/queries.ts` — `useSessionStats()`, `useSessions()`
- `services/api/app/service/sessions.py` — `get_stats()` (dashboard aggregates)

## Canonical Files
- Dashboard page: `apps/web/src/app/page.tsx`
- Stats service logic: `services/api/app/service/sessions.py`

## Inputs
- None (the dashboard loads data automatically)

## Outputs
- `GET /sessions/stats` → `SessionStats` (total/trained/running sessions, total frames,
  source/derived/total bytes, `total_bytes_human`, `avg_write_amplification`)
- `GET /sessions` → `Session[]` for the write-amplification chart and the recent-sessions panel

## Flow
- Page loads → the stat cards and the write-amplification chart fetch in parallel through
  TanStack Query hooks; the recent-sessions panel links straight into each session's detail page

## Edge Cases
- No sessions yet → empty states on the cards, chart, and recent-sessions panel
- No runs yet → write-amplification is 0 (no divide-by-zero)
- API unavailable → inline `ErrorState` with retry

## UX States
- Loading: skeletons on the cards, chart, and recent-sessions grid
- Empty: "No sessions yet" / "No runs yet" prompts
- Loaded: populated cards, chart, and recent sessions

## Verification
- Test files: `services/api/tests/test_sessions.py`, `apps/web/src/lib/queries.test.ts`
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green; the dashboard renders session stats

## Related Docs
- [Write amplification](write-amplification.md) — the metric and the per-session storage explorer
- [Sessions](sessions.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
