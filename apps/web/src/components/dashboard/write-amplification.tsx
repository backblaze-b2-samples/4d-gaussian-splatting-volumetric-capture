"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { TrendingUp } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useSessions } from "@/lib/queries";

const chartConfig = {
  source: { label: "Source (MB)", color: "var(--chart-2)" },
  derived: { label: "Derived (MB)", color: "var(--chart-1)" },
} satisfies ChartConfig;

export function WriteAmplification() {
  const { data: sessions, isLoading, error, refetch } = useSessions();

  const data = useMemo(
    () =>
      (sessions ?? [])
        .filter((s) => s.metrics.source_bytes > 0)
        .slice(0, 8)
        .map((s) => ({
          name: s.name.length > 14 ? `${s.name.slice(0, 13)}…` : s.name,
          source: +(s.metrics.source_bytes / 1_000_000).toFixed(2),
          derived: +(
            (s.metrics.frame_bytes +
              s.metrics.checkpoint_bytes +
              s.metrics.model_bytes) /
            1_000_000
          ).toFixed(2),
        })),
    [sessions],
  );

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">B2 write amplification</CardTitle>
        <CardDescription className="text-xs">
          Source video vs. derived bytes per session
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <Skeleton className="h-[240px] w-full" />
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={TrendingUp}
            title="No runs yet"
            description="Run a session to see how its source video fans out into frames and model artifacts."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tickLine={false} axisLine={false} tickMargin={10} fontSize={11} />
              <YAxis tickLine={false} axisLine={false} tickMargin={6} fontSize={11} width={32} />
              <ChartTooltip cursor={{ fill: "var(--accent-subtle)" }} content={<ChartTooltipContent />} />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar dataKey="source" fill="var(--color-source)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="derived" fill="var(--color-derived)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
