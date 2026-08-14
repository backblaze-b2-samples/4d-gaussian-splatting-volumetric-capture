"use client";

import { use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Pencil, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { SessionStatusPill } from "@/components/sessions/session-status";
import { SessionPreview } from "@/components/sessions/session-preview";
import { StageTimeline } from "@/components/sessions/stage-timeline";
import { StorageBreakdown } from "@/components/sessions/storage-breakdown";
import { TrainCommand } from "@/components/sessions/train-command";
import { useDeleteSession, useRunSession, useSession } from "@/lib/queries";
import { scenePresetLabel } from "@/lib/session-options";

export default function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { data: session, isLoading, error, refetch } = useSession(id);
  const run = useRunSession(id);
  const remove = useDeleteSession();

  const running = session?.status === "running";
  const preRun = session?.status === "draft" || session?.status === "ready";

  const onRun = async () => {
    try {
      await run.mutateAsync();
      toast.success("Run started", {
        description: "The pipeline stages will advance live below.",
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't start the run");
    }
  };

  const onDelete = async () => {
    try {
      await remove.mutateAsync(id);
      toast.success("Session deleted");
      router.push("/sessions");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't delete the session");
    }
  };

  if (isLoading) return <Skeleton className="h-[60vh] w-full" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!session) return null;

  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="page-title truncate">{session.name}</h1>
            <SessionStatusPill status={session.status} />
          </div>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {scenePresetLabel(session.params.scene_preset)} ·{" "}
            {session.params.num_cameras} cameras ·{" "}
            {session.params.frames_per_camera} frames · {session.params.quality}
          </p>
          {session.error && (
            <p className="mt-1 text-sm text-destructive">{session.error}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button size="sm" className="h-8" onClick={onRun} disabled={running || run.isPending}>
            <Play className="h-3.5 w-3.5" />
            {running || run.isPending
              ? "Running..."
              : session.status === "done"
                ? "Re-run"
                : "Run"}
          </Button>
          {preRun && (
            <Button asChild size="sm" variant="outline" className="h-8">
              <Link href={`/sessions/${id}/edit`}>
                <Pencil className="h-3.5 w-3.5" />
                Edit
              </Link>
            </Button>
          )}
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button size="sm" variant="outline" className="h-8" disabled={running}>
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this session?</AlertDialogTitle>
                <AlertDialogDescription>
                  This permanently removes the manifest and every B2 object under
                  this session&apos;s prefixes (source video, frames, calibration,
                  dataset, checkpoints, model). This cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={onDelete}>Delete</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <SessionPreview previewKey={session.preview_key} />
          <StageTimeline stages={session.stages} />
          <TrainCommand session={session} />
        </div>
        <div className="space-y-6">
          <MetricsCard session={session} />
          <StorageBreakdown sessionId={id} status={session.status} />
        </div>
      </div>
    </div>
  );
}

function MetricsCard({
  session,
}: {
  session: NonNullable<ReturnType<typeof useSession>["data"]>;
}) {
  const m = session.metrics;
  const rows: [string, string][] = [
    ["Cameras", String(m.num_cameras)],
    ["Frames / camera", String(m.frames_per_camera)],
    ["Frames extracted", String(m.total_frames)],
    ["Init cloud points", String(m.init_points)],
    ["Device", m.device],
    ["Trained", m.trained ? "yes" : "no (CUDA required)"],
  ];
  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">4D metrics</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
          {rows.map(([label, value]) => (
            <div key={label} className="min-w-0">
              <dt className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {label}
              </dt>
              <dd className="mt-0.5 truncate font-medium tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
