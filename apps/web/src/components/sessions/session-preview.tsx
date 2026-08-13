"use client";

/* eslint-disable @next/next/no-img-element */
import { Boxes } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { usePreviewUrl } from "@/lib/queries";

// Renders the multi-view contact-sheet preview PNG stored under the session's
// `previews/` prefix, via the same presigned inline-preview endpoint the file
// explorer uses. A plain <img> (not next/image) keeps it dependency-free for a
// short-lived signed B2 URL.
export function SessionPreview({ previewKey }: { previewKey: string | null }) {
  const { data, isLoading } = usePreviewUrl(previewKey ?? undefined, !!previewKey);

  if (!previewKey) {
    return (
      <div className="flex aspect-video w-full items-center justify-center rounded-md border border-border bg-muted/30 text-muted-foreground">
        <div className="flex flex-col items-center gap-2 text-sm">
          <Boxes className="h-6 w-6" />
          No preview yet — run the session
        </div>
      </div>
    );
  }

  if (isLoading || !data) {
    return <Skeleton className="aspect-video w-full rounded-md" />;
  }

  return (
    <img
      src={data.url}
      alt="Synchronized multi-view contact sheet and init point cloud"
      className="aspect-video w-full rounded-md border border-border bg-muted/30 object-contain"
    />
  );
}
