"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import type { DataResidencyRegion } from "@/lib/types/domain";
import { Badge } from "@/components/ui/badge";
import { cn, formatNumber } from "@/lib/utils";

const DataResidencyLeafletMap = dynamic(
  () =>
    import("./data-residency-map-leaflet").then((mod) => mod.DataResidencyLeafletMap),
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

const statusVariant = {
  compliant: "success" as const,
  review: "warning" as const,
  "at-risk": "destructive" as const,
};

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

export function DataResidencyMap({ regions = [], className }: DataResidencyMapProps) {
  const [activeId, setActiveId] = useState<string | null>(regions[0]?.id ?? null);
  const active = regions.find((r) => r.id === activeId) ?? regions[0];

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
      <DataResidencyLeafletMap
        regions={regions}
        activeId={activeId}
        onSelectRegion={setActiveId}
      />

      {active && <RegionDetailPanel region={active} />}

      <RegionSwitcher regions={regions} activeId={activeId} onSelect={setActiveId} />
    </div>
  );
}
