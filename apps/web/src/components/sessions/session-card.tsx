import Link from "next/link";
import { Boxes, Film, Layers } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { SessionStatusPill } from "./session-status";
import { scenePresetLabel } from "@/lib/session-options";
import { formatDate } from "@/lib/utils";
import type { Session } from "@4d-gaussian-splatting-volumetric-capture/shared";

export function SessionCard({ session }: { session: Session }) {
  const { params, metrics } = session;
  return (
    <Link href={`/sessions/${session.id}`} className="block">
      <Card className="card-hover h-full">
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="truncate font-semibold" title={session.name}>
                {session.name}
              </h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {scenePresetLabel(params.scene_preset)}
              </p>
            </div>
            <SessionStatusPill status={session.status} />
          </div>

          <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <Boxes className="h-3.5 w-3.5" />
              {params.num_cameras} cams
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Film className="h-3.5 w-3.5" />
              {params.frames_per_camera} frames
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5" />
              {metrics.total_frames > 0
                ? `${metrics.total_frames} extracted`
                : params.quality}
            </span>
          </div>

          <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
            <span>{formatDate(session.created_at)}</span>
            {metrics.write_amplification > 0 && (
              <span className="font-mono tabular-nums text-[var(--brand-b2)]">
                {metrics.write_amplification.toFixed(1)}x write-amp
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
