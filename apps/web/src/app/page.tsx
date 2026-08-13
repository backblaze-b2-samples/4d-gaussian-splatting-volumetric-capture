"use client";

import Link from "next/link";
import { Boxes, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SessionStatsCards } from "@/components/dashboard/session-stats-cards";
import { WriteAmplification } from "@/components/dashboard/write-amplification";
import { SessionCard } from "@/components/sessions/session-card";
import { useSessions } from "@/lib/queries";

export default function DashboardPage() {
  const { data: sessions = [], isLoading, error, refetch } = useSessions();
  const recent = sessions.slice(0, 4);

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5 max-w-prose">
            4D volumetric capture sessions and their B2 write-amplification —
            how source video fans out into frames, checkpoints, and trained
            splat models on Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/sessions/new">
            <Plus className="h-3.5 w-3.5" />
            New session
          </Link>
        </Button>
      </div>

      <SessionStatsCards />

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <WriteAmplification />
        </div>
        <div className="animate-fade-in-up stagger-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="card-title">Recent sessions</h2>
            <Link
              href="/sessions"
              className="text-xs font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            >
              View all
            </Link>
          </div>
          {isLoading ? (
            <div className="grid gap-4 sm:grid-cols-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-40 w-full" />
              ))}
            </div>
          ) : error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : recent.length === 0 ? (
            <EmptyState
              icon={Boxes}
              title="No sessions yet"
              description="Create a 4D capture session to stage a multi-view dataset on B2 and see the write-amplification story."
              action={
                <Button asChild size="sm">
                  <Link href="/sessions/new">
                    <Plus className="h-3.5 w-3.5" />
                    New session
                  </Link>
                </Button>
              }
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {recent.map((session) => (
                <SessionCard key={session.id} session={session} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
