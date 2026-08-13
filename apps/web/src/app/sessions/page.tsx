"use client";

import Link from "next/link";
import { Boxes, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SessionCard } from "@/components/sessions/session-card";
import { useSessions } from "@/lib/queries";

export default function SessionsPage() {
  const { data: sessions = [], isLoading, error, refetch } = useSessions();

  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Sessions</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            4D volumetric capture sessions. Each turns synchronized multi-camera
            video into a 4DGaussians dataset and trained splat, versioned in
            Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8 shrink-0">
          <Link href="/sessions/new">
            <Plus className="h-3.5 w-3.5" />
            New session
          </Link>
        </Button>
      </div>

      <div className="animate-fade-in-up stagger-2">
        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-40 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : sessions.length === 0 ? (
          <EmptyState
            icon={Boxes}
            title="No sessions yet"
            description="Create your first 4D capture session to stage a multi-view dataset on B2."
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
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sessions.map((session) => (
              <SessionCard key={session.id} session={session} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
