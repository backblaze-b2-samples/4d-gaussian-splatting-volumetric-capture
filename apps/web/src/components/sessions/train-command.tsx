"use client";

import { useState } from "react";
import { Check, Copy, Cpu } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Session } from "@4d-gaussian-splatting-volumetric-capture/shared";

// Shows the EXACT hustvl/4DGaussians train.py command for the CUDA tail. On a
// non-CUDA host the train/export stages are skipped and this is the command to
// copy-paste on a CUDA box — the trained splat is never faked.
export function TrainCommand({ session }: { session: Session }) {
  const [copied, setCopied] = useState(false);
  const command = session.train_command;

  if (!command) return null;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      toast.success("Command copied");
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Couldn't copy to clipboard");
    }
  };

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title flex items-center gap-2">
          <Cpu className="h-4 w-4" />
          4DGaussians training (CUDA)
        </CardTitle>
        <CardDescription className="text-xs">
          {session.metrics.trained
            ? `Trained on ${session.metrics.device}.`
            : "CUDA-only. The dataset + init cloud are already staged on B2 — run this on a CUDA host to train the splat."}
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5 space-y-3">
        <div className="relative">
          <pre className="overflow-x-auto rounded-md border border-border bg-muted/40 p-3 pr-12 font-mono text-xs leading-relaxed">
            <code>{command}</code>
          </pre>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Copy train command"
            className="absolute right-2 top-2 h-7 w-7"
            onClick={copy}
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          First run <code>scripts/setup_engine.sh</code> to clone the engine and
          its CUDA submodules, then set <code>FOURDGS_REPO_DIR</code>.
        </p>
      </CardContent>
    </Card>
  );
}
