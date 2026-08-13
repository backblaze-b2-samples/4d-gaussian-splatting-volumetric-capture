import { SessionForm } from "@/components/sessions/session-form";

export default function NewSessionPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">New session</h1>
        <p className="mt-1.5 max-w-prose text-sm text-pretty text-muted-foreground">
          Pick a synthetic scene and capture parameters. The defaults are sized
          for a fast, sound test run — change them if you want the scale story.
          Running the session generates the multi-view capture, stages the
          dataset on B2, and emits the 4DGaussians training command.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <SessionForm mode="create" />
      </div>
    </div>
  );
}
