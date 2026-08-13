import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { STAGE_LABELS, STAGE_STATUS_DOT } from "@/lib/session-options";
import type { SessionStage } from "@4d-gaussian-splatting-volumetric-capture/shared";

export function StageTimeline({ stages }: { stages: SessionStage[] }) {
  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Pipeline stages</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
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
