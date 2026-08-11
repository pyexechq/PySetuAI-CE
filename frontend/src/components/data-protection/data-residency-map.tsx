"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { MapPin, MapPinned } from "lucide-react";
import type { DataResidencyRegion } from "@/lib/types/domain";
import { Badge } from "@/components/ui/badge";
import { cn, formatNumber } from "@/lib/utils";

const statusVariant = {
  compliant: "success" as const,
  review: "warning" as const,
  "at-risk": "destructive" as const,
};

const DataResidencyGoogleMap = dynamic(
  () =>
    import("./data-residency-map-google").then((mod) => mod.DataResidencyGoogleMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[320px] w-full items-center justify-center rounded-lg border border-border/60 bg-muted/20">
        <p className="text-sm text-muted-foreground">Loading map…</p>
      </div>
    ),
  }
);

interface DataResidencyMapProps {
  regions?: DataResidencyRegion[];
  className?: string;
}

function RegionDetailPanel({ region }: { region: DataResidencyRegion }) {
  return (
    <div className="rounded-lg border border-border/60 bg-muted/10 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="h-3 w-3 rounded-full" style={{ backgroundColor: region.color }} />
        <span className="font-medium">{region.name}</span>
        <Badge variant={statusVariant[region.status]}>{region.status}</Badge>
        <span className="text-sm text-muted-foreground">
          {formatNumber(region.records)} records ({region.percentage}%)
        </span>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{region.policy}</p>
      <p className="mt-1 text-xs text-muted-foreground">Hubs: {region.hubs.join(" · ")}</p>
    </div>
  );
}

function RegionSwitcher({
  regions,
  activeId,
  onSelect,
}: {
  regions: DataResidencyRegion[];
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap justify-center gap-4">
      {regions.map((region) => (
        <button
          key={region.id}
          type="button"
          onClick={() => onSelect(region.id)}
          className={cn(
            "flex items-center gap-2 rounded-md px-2 py-1 text-xs transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            activeId === region.id ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted/50"
          )}
        >
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: region.color }} />
          {region.name}
        </button>
      ))}
    </div>
  );
}

function ResidencyDistributionFallback({
  regions,
  activeId,
  onSelect,
}: {
  regions: DataResidencyRegion[];
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  const maxPercentage = Math.max(...regions.map((r) => r.percentage), 1);

  return (
    <div
      className="space-y-4 rounded-lg border border-border/60 bg-muted/10 p-4"
      role="group"
      aria-label="Data residency distribution"
    >
      <div className="flex items-start gap-3 rounded-md border border-dashed border-border/70 bg-background/60 p-3">
        <MapPinned className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" aria-hidden />
        <div>
          <p className="text-sm font-medium">Interactive map unavailable</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Add{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-[11px]">
              NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
            </code>{" "}
            to <code className="rounded bg-muted px-1 py-0.5 text-[11px]">frontend/.env.local</code>{" "}
            to enable zoomable Google Maps with hub markers.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {regions.map((region) => {
          const isActive = activeId === region.id;
          const barWidth = (region.percentage / maxPercentage) * 100;

          return (
            <button
              key={region.id}
              type="button"
              onClick={() => onSelect(region.id)}
              onMouseEnter={() => onSelect(region.id)}
              onFocus={() => onSelect(region.id)}
              aria-pressed={isActive}
              className={cn(
                "w-full rounded-md border p-3 text-left transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                isActive ? "border-border bg-background shadow-sm" : "border-transparent hover:bg-background/60"
              )}
            >
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: region.color }} />
                <span className="text-sm font-medium">{region.name}</span>
                <Badge variant={statusVariant[region.status]} className="text-[10px]">
                  {region.status}
                </Badge>
                <span className="ml-auto text-sm font-semibold tabular-nums" style={{ color: region.color }}>
                  {region.percentage}%
                </span>
              </div>

              <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{ width: `${barWidth}%`, backgroundColor: region.color }}
                />
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                <span>{formatNumber(region.records)} records</span>
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3 w-3" aria-hidden />
                  {region.hubs.join(" · ")}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function DataResidencyMap({ regions = [], className }: DataResidencyMapProps) {
  const [activeId, setActiveId] = useState<string | null>(regions[0]?.id ?? null);
  const active = regions.find((r) => r.id === activeId) ?? regions[0];

  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY?.trim();
  const hasMapKey = Boolean(apiKey);

  if (regions.length === 0) {
    return (
      <div className={cn("rounded-lg border border-dashed border-border/70 bg-muted/10 p-8 text-center", className)}>
        <p className="text-sm font-medium">No residency regions configured</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Regional placement data will appear when data residency policies are tracked in audit logs.
        </p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      {hasMapKey && apiKey ? (
        <DataResidencyGoogleMap
          apiKey={apiKey}
          regions={regions}
          activeId={activeId}
          onSelectRegion={setActiveId}
        />
      ) : (
        <ResidencyDistributionFallback
          regions={regions}
          activeId={activeId}
          onSelect={setActiveId}
        />
      )}

      {active && <RegionDetailPanel region={active} />}

      <RegionSwitcher regions={regions} activeId={activeId} onSelect={setActiveId} />
    </div>
  );
}
