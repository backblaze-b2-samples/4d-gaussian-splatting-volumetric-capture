import { STATUS_STYLES } from "@/lib/session-options";
import type { SessionStatus } from "@4d-gaussian-splatting-volumetric-capture/shared";

export function SessionStatusPill({ status }: { status: SessionStatus }) {
  const style = STATUS_STYLES[status];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {style.label}
    </span>
  );
}
