"use client";

import { useEffect, useMemo } from "react";
import {
  APIProvider,
  AdvancedMarker,
  Circle,
  ColorScheme,
  Map,
  useMap,
} from "@vis.gl/react-google-maps";
import { useTheme } from "next-themes";
import type { DataResidencyRegion } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const WORLD_CENTER = { lat: 25, lng: 10 };
const WORLD_ZOOM = 2;

/** Primary region centers for map focus and coverage circles. */
export const REGION_COORDS: Record<
  string,
  { lat: number; lng: number; zoom: number }
> = {
  us: { lat: 38.9, lng: -77.0, zoom: 4 },
  eu: { lat: 50.1, lng: 8.7, zoom: 4 },
  apac: { lat: 1.35, lng: 103.8, zoom: 4 },
};

/** Individual hub cities per region. */
export const HUB_COORDS: Record<
  string,
  { name: string; lat: number; lng: number }[]
> = {
  us: [
    { name: "Virginia", lat: 38.9072, lng: -77.0369 },
    { name: "Oregon", lat: 45.5152, lng: -122.6784 },
  ],
  eu: [
    { name: "Frankfurt", lat: 50.1109, lng: 8.6821 },
    { name: "Dublin", lat: 53.3498, lng: -6.2603 },
  ],
  apac: [
    { name: "Singapore", lat: 1.3521, lng: 103.8198 },
    { name: "Sydney", lat: -33.8688, lng: 151.2093 },
  ],
};

function circleRadiusMeters(percentage: number) {
  return percentage * 35_000;
}

interface RegionMarkerProps {
  region: DataResidencyRegion;
  isActive: boolean;
  onSelect: () => void;
}

function RegionMarker({ region, isActive, onSelect }: RegionMarkerProps) {
  const coords = REGION_COORDS[region.id];
  if (!coords) return null;

  return (
    <AdvancedMarker
      position={{ lat: coords.lat, lng: coords.lng }}
      onClick={onSelect}
      title={`${region.name}: ${region.percentage}%`}
      zIndex={isActive ? 100 : 10}
    >
      <button
        type="button"
        onClick={onSelect}
        aria-label={`${region.name}: ${region.percentage}% of records`}
        aria-pressed={isActive}
        className={cn(
          "flex flex-col items-center gap-0.5 rounded-md border-2 border-white bg-white/95 px-2 py-1 shadow-md transition-transform dark:border-slate-800 dark:bg-slate-900/95",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          isActive ? "scale-110" : "scale-100 hover:scale-105"
        )}
      >
        <span
          className="text-xs font-bold tabular-nums leading-none"
          style={{ color: region.color }}
        >
          {region.percentage}%
        </span>
        <span className="whitespace-nowrap text-[10px] font-medium leading-none text-muted-foreground">
          {region.name.replace(" Region", "")}
        </span>
      </button>
    </AdvancedMarker>
  );
}

function MapCameraSync({
  activeId,
  regions,
}: {
  activeId: string | null;
  regions: DataResidencyRegion[];
}) {
  const map = useMap();

  useEffect(() => {
    if (!map || !activeId) return;
    const coords = REGION_COORDS[activeId];
    if (!coords) return;
    map.panTo({ lat: coords.lat, lng: coords.lng });
    map.setZoom(coords.zoom);
  }, [map, activeId]);

  useEffect(() => {
    if (!map || regions.length === 0) return;
    if (activeId) return;
    map.panTo(WORLD_CENTER);
    map.setZoom(WORLD_ZOOM);
  }, [map, activeId, regions.length]);

  return null;
}

interface DataResidencyGoogleMapProps {
  apiKey: string;
  regions: DataResidencyRegion[];
  activeId: string | null;
  onSelectRegion: (id: string) => void;
  className?: string;
}

export function DataResidencyGoogleMap({
  apiKey,
  regions,
  activeId,
  onSelectRegion,
  className,
}: DataResidencyGoogleMapProps) {
  const { resolvedTheme } = useTheme();

  const colorScheme = useMemo(
    () => (resolvedTheme === "dark" ? ColorScheme.DARK : ColorScheme.LIGHT),
    [resolvedTheme]
  );

  return (
    <APIProvider apiKey={apiKey}>
      <div
        className={cn(
          "relative h-[320px] w-full overflow-hidden rounded-lg border border-border/60",
          className
        )}
        role="group"
        aria-label="Interactive data residency map"
      >
        <Map
          defaultCenter={WORLD_CENTER}
          defaultZoom={WORLD_ZOOM}
          gestureHandling="greedy"
          disableDefaultUI={false}
          zoomControl
          mapTypeControl={false}
          streetViewControl={false}
          fullscreenControl
          colorScheme={colorScheme}
          style={{ width: "100%", height: "100%" }}
          onClick={() => onSelectRegion(activeId ?? regions[0]?.id ?? "")}
        >
          <MapCameraSync activeId={activeId} regions={regions} />

          {regions.map((region) => {
            const coords = REGION_COORDS[region.id];
            if (!coords) return null;
            const isActive = activeId === region.id;

            return (
              <Circle
                key={`circle-${region.id}`}
                center={{ lat: coords.lat, lng: coords.lng }}
                radius={circleRadiusMeters(region.percentage)}
                fillColor={region.color}
                fillOpacity={isActive ? 0.28 : 0.14}
                strokeColor={region.color}
                strokeOpacity={isActive ? 0.85 : 0.45}
                strokeWeight={isActive ? 2.5 : 1.5}
                clickable
                onClick={() => onSelectRegion(region.id)}
              />
            );
          })}

          {regions.flatMap((region) => {
            const hubs = HUB_COORDS[region.id] ?? [];
            return hubs.map((hub) => (
              <AdvancedMarker
                key={`hub-${region.id}-${hub.name}`}
                position={{ lat: hub.lat, lng: hub.lng }}
                onClick={() => onSelectRegion(region.id)}
                title={`${hub.name} — ${region.name}`}
                zIndex={activeId === region.id ? 50 : 5}
              >
                <div
                  className="h-2.5 w-2.5 rounded-full border-2 border-white shadow-sm dark:border-slate-900"
                  style={{ backgroundColor: region.color }}
                />
              </AdvancedMarker>
            ));
          })}

          {regions.map((region) => (
            <RegionMarker
              key={`marker-${region.id}`}
              region={region}
              isActive={activeId === region.id}
              onSelect={() => onSelectRegion(region.id)}
            />
          ))}
        </Map>
      </div>
    </APIProvider>
  );
}
