"use client";

import { Boxes, Film, HardDrive, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useSessionStats } from "@/lib/queries";

export function SessionStatsCards() {
  const { data: stats, isLoading, error, refetch } = useSessionStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cards = [
    { title: "Sessions", value: stats?.total_sessions ?? 0, icon: Boxes },
    { title: "Frames extracted", value: stats?.total_frames ?? 0, icon: Film },
    {
      title: "B2 footprint",
      value: stats?.total_bytes_human ?? "0 B",
      icon: HardDrive,
    },
    {
      title: "Avg write-amp",
      value: stats ? `${stats.avg_write_amplification.toFixed(2)}x` : "0x",
      icon: TrendingUp,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <Card
          key={card.title}
          className={`card-hover animate-fade-in-up stagger-${i + 1}`}
        >
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="stat-value">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
