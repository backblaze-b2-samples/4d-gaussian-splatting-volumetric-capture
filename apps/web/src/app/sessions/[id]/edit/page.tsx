"use client";

import { use } from "react";
import Link from "next/link";
import { Lock } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SessionForm } from "@/components/sessions/session-form";
import { useSession } from "@/lib/queries";

export default function EditSessionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: session, isLoading, error, refetch } = useSession(id);

  const locked =
    session && session.status !== "draft" && session.status !== "ready";

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Edit session</h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Capture parameters can be changed until the session has run.
        </p>
      </div>

      {isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !session ? null : locked ? (
        <Alert>
          <Lock />
          <AlertTitle>Parameters are locked</AlertTitle>
          <AlertDescription>
            <span>
              This session has already run, so its capture parameters are fixed.
              Create a new session to change them.{" "}
              <Link
                href={`/sessions/${id}`}
                className="font-medium underline underline-offset-4"
              >
                Back to session
              </Link>
              .
            </span>
          </AlertDescription>
        </Alert>
      ) : (
        <div className="animate-fade-in-up stagger-2">
          <SessionForm mode="edit" session={session} />
        </div>
      )}

      {!isLoading && !error && (
        <Button asChild variant="ghost" size="sm">
          <Link href={`/sessions/${id}`}>Cancel</Link>
        </Button>
      )}
    </div>
  );
}
