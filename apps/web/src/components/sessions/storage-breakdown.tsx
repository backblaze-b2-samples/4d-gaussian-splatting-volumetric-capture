"use client";

import { HardDrive } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useSessionStorage } from "@/lib/queries";

// The sample's own scoped explorer: one session's B2 footprint by pipeline
// stage, with the write-amplification breakdown (source video -> derived bytes).
export function StorageBreakdown({ sessionId }: { sessionId: string }) {
  const { data, isLoading, error, refetch } = useSessionStorage(sessionId);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Artifacts &amp; storage</CardTitle>
        <CardDescription className="text-xs">
          Per-stage B2 footprint for this session, scoped to its own prefixes.
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : !data || data.total_objects === 0 ? (
          <EmptyState
            icon={HardDrive}
            title="No artifacts yet"
            description="Run the session to stage frames, calibration and the dataset to B2."
          />
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <Metric label="Source" value={humanize(data.source_bytes)} />
              <Metric label="Derived" value={humanize(data.derived_bytes)} />
              <Metric
                label="Write amp."
                value={`${data.write_amplification.toFixed(2)}x`}
                accent
              />
            </div>
            <div className="space-y-2">
              {data.stages.map((s) => {
                const pct =
                  data.total_bytes > 0 ? (s.bytes / data.total_bytes) * 100 : 0;
                return (
                  <div key={s.stage} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium capitalize">{s.stage}</span>
                      <span className="font-mono tabular-nums text-muted-foreground">
                        {s.object_count} obj · {s.bytes_human}
                      </span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-[var(--brand-b2)]"
                        style={{ width: `${Math.max(pct, s.bytes > 0 ? 2 : 0)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              {data.total_objects} objects · {humanize(data.total_bytes)} total in
              Backblaze B2.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div
        className={`mt-1 text-lg font-semibold tabular-nums ${accent ? "text-[var(--brand-b2)]" : ""}`}
      >
        {value}
      </div>
    </div>
  );
}

function humanize(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}
