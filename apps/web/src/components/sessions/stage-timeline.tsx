import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { STAGE_LABELS, STAGE_STATUS_DOT } from "@/lib/session-options";
import type { SessionStage } from "@4d-gaussian-splatting-volumetric-capture/shared";

// A stage is "settled" once it reaches any terminal state (done / skipped on a
// non-CUDA host / failed), so the overall bar advances as the run progresses.
const SETTLED_STAGE_STATUSES: ReadonlySet<SessionStage["status"]> = new Set([
  "done",
  "skipped",
  "failed",
]);

export function StageTimeline({ stages }: { stages: SessionStage[] }) {
  const total = stages.length;
  const settled = stages.filter((s) =>
    SETTLED_STAGE_STATUSES.has(s.status),
  ).length;
  const pct = total > 0 ? Math.round((settled / total) * 100) : 0;

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Pipeline stages</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        {total > 0 && (
          <div className="mb-4 space-y-1.5">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Overall progress</span>
              <span className="tabular-nums">
                {settled}/{total} stages · {pct}%
              </span>
            </div>
            <Progress value={pct} aria-label="Overall pipeline progress" />
          </div>
        )}
        <ol className="space-y-3">
          {stages.map((stage) => (
            <li key={stage.name} className="flex items-start gap-3">
              <span
                className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${STAGE_STATUS_DOT[stage.status]}`}
                aria-hidden
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">
                    {STAGE_LABELS[stage.name] ?? stage.name}
                  </span>
                  <span className="text-xs uppercase tracking-wider text-muted-foreground">
                    {stage.status}
                  </span>
                </div>
                {stage.message && (
                  <p className="mt-0.5 break-words text-xs text-muted-foreground">
                    {stage.message}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
