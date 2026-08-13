"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useCreateSession, useUpdateSession } from "@/lib/queries";
import {
  CREATE_DEFAULTS,
  FRAMES_PER_CAMERA_OPTIONS,
  NUM_CAMERAS_OPTIONS,
  QUALITY_OPTIONS,
  SCENE_PRESETS,
} from "@/lib/session-options";
import type {
  FramesPerCamera,
  NumCameras,
  Quality,
  ScenePreset,
  Session,
} from "@4d-gaussian-splatting-volumetric-capture/shared";

// Finite-option fields are Selects (never free text) and validated as enums, so
// the form and the API's Literal boundary can never drift.
const schema = z.object({
  name: z.string().min(1, "Give the session a name").max(120),
  scene_preset: z.enum(["orbit-dancer", "bouncing-prims", "rotating-bust"]),
  num_cameras: z.enum(["4", "8", "12", "20"]),
  frames_per_camera: z.enum(["12", "24", "48"]),
  quality: z.enum(["draft", "balanced", "high"]),
});

type FormValues = z.infer<typeof schema>;

export function SessionForm({
  mode,
  session,
}: {
  mode: "create" | "edit";
  session?: Session;
}) {
  const router = useRouter();
  const create = useCreateSession();
  const update = useUpdateSession(session?.id ?? "");
  const pending = create.isPending || update.isPending;

  const defaults: FormValues =
    mode === "edit" && session
      ? {
          name: session.name,
          scene_preset: session.params.scene_preset,
          num_cameras: String(session.params.num_cameras) as FormValues["num_cameras"],
          frames_per_camera: String(
            session.params.frames_per_camera
          ) as FormValues["frames_per_camera"],
          quality: session.params.quality,
        }
      : {
          name: "",
          scene_preset: CREATE_DEFAULTS.scene_preset,
          num_cameras: String(CREATE_DEFAULTS.num_cameras) as FormValues["num_cameras"],
          frames_per_camera: String(
            CREATE_DEFAULTS.frames_per_camera
          ) as FormValues["frames_per_camera"],
          quality: CREATE_DEFAULTS.quality,
        };

  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: defaults });

  const onSubmit = async (values: FormValues) => {
    const params = {
      scene_preset: values.scene_preset as ScenePreset,
      num_cameras: Number(values.num_cameras) as NumCameras,
      frames_per_camera: Number(values.frames_per_camera) as FramesPerCamera,
      quality: values.quality as Quality,
    };
    try {
      if (mode === "edit" && session) {
        await update.mutateAsync({ name: values.name, ...params });
        toast.success("Session updated");
        router.push(`/sessions/${session.id}`);
      } else {
        const created = await create.mutateAsync({ name: values.name, ...params });
        toast.success("Session created");
        router.push(`/sessions/${created.id}`);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Something went wrong");
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Capture parameters</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-6">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Session name</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Studio dancer take 1" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="scene_preset"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Scene preset</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full sm:w-72">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {SCENE_PRESETS.map((p) => (
                        <SelectItem key={p.value} value={p.value}>
                          {p.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Synthetic, license-clean subjects — no real people. Default:{" "}
                    <code>orbit-dancer</code>.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-6 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="num_cameras"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Cameras</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {NUM_CAMERAS_OPTIONS.map((n) => (
                          <SelectItem key={n} value={String(n)}>
                            {n} cameras
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Synchronized views of the scene. Default: 4 (fast test run).
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="frames_per_camera"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Frames per camera</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {FRAMES_PER_CAMERA_OPTIONS.map((n) => (
                          <SelectItem key={n} value={String(n)}>
                            {n} frames
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Temporal length of the 4D capture. Default: 12.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="quality"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Training quality</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full sm:w-72">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {QUALITY_OPTIONS.map((q) => (
                        <SelectItem key={q.value} value={q.value}>
                          {q.label} — {q.hint}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Maps to the 4DGaussians iteration budget + resolution.
                    Default: <code>draft</code>.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
            disabled={pending}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={pending}>
            {pending
              ? "Saving..."
              : mode === "edit"
                ? "Save changes"
                : "Create session"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
