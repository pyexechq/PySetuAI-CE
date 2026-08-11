"use client";

import { useEffect, useMemo } from "react";
import L from "leaflet";
import { Circle, MapContainer, Marker, TileLayer, useMap } from "react-leaflet";
import { useTheme } from "next-themes";
import type { DataResidencyRegion } from "@/lib/types/domain";
import {
  HUB_COORDS,
  REGION_COORDS,
  WORLD_CENTER,
  WORLD_ZOOM,
  circleRadiusMeters,
} from "@/components/data-protection/data-residency-coords";
import { cn } from "@/lib/utils";

const TILE_LIGHT = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_DARK = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";

function MapCameraSync({
  activeId,
  regions,
}: {
  activeId: string | null;
  regions: DataResidencyRegion[];
}) {
  const map = useMap();

  useEffect(() => {
    if (!activeId) return;
    const coords = REGION_COORDS[activeId];
    if (!coords) return;
    map.flyTo([coords.lat, coords.lng], coords.zoom, { duration: 0.75 });
  }, [map, activeId]);

  useEffect(() => {
    if (regions.length === 0 || activeId) return;
    map.flyTo([WORLD_CENTER.lat, WORLD_CENTER.lng], WORLD_ZOOM, { duration: 0.75 });
  }, [map, activeId, regions.length]);

  return null;
}

function regionMarkerIcon(region: DataResidencyRegion, isActive: boolean) {
  const shortNames: Record<string, string> = { eu: "EU", us: "US", apac: "APAC" };
  const shortName = shortNames[region.id] ?? region.name.replace(" Region", "");

  return L.divIcon({
    className: "",
    html: `
      <div class="flex flex-col items-center gap-0.5 rounded-md border-2 border-white bg-white/95 px-2 py-1 shadow-md dark:border-slate-800 dark:bg-slate-900/95 ${
        isActive ? "scale-110" : "scale-100"
      }" style="transform: ${isActive ? "scale(1.1)" : "scale(1)"};">
        <span class="text-xs font-bold tabular-nums leading-none" style="color:${region.color}">${region.percentage}%</span>
        <span class="whitespace-nowrap text-[10px] font-medium leading-none text-slate-500">${shortName}</span>
      </div>
    `,
    iconSize: [72, 40],
    iconAnchor: [36, 20],
  });
}

function hubMarkerIcon(color: string) {
  return L.divIcon({
    className: "",
    html: `<div class="h-2.5 w-2.5 rounded-full border-2 border-white shadow-sm dark:border-slate-900" style="background-color:${color}"></div>`,
    iconSize: [10, 10],
    iconAnchor: [5, 5],
  });
}

interface DataResidencyLeafletMapProps {
  regions: DataResidencyRegion[];
  activeId: string | null;
  onSelectRegion: (id: string) => void;
  className?: string;
}

export function DataResidencyLeafletMap({
  regions,
  activeId,
  onSelectRegion,
  className,
}: DataResidencyLeafletMapProps) {
  const { resolvedTheme } = useTheme();

  const tileUrl = useMemo(
    () => (resolvedTheme === "dark" ? TILE_DARK : TILE_LIGHT),
    [resolvedTheme]
  );

  const tileAttribution =
    resolvedTheme === "dark"
      ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
      : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

  return (
    <div
      className={cn(
        "relative h-[320px] w-full overflow-hidden rounded-lg border border-border/60 [&_.leaflet-control-attribution]:text-[10px]",
        className
      )}
      role="group"
      aria-label="Interactive data residency map"
    >
      <MapContainer
        center={[WORLD_CENTER.lat, WORLD_CENTER.lng]}
        zoom={WORLD_ZOOM}
        scrollWheelZoom
        className="h-full w-full"
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer url={tileUrl} attribution={tileAttribution} />
        <MapCameraSync activeId={activeId} regions={regions} />

        {regions.map((region) => {
          const coords = REGION_COORDS[region.id];
          if (!coords) return null;
          const isActive = activeId === region.id;

          return (
            <Circle
              key={`circle-${region.id}`}
              center={[coords.lat, coords.lng]}
              radius={circleRadiusMeters(region.percentage)}
              pathOptions={{
                color: region.color,
                fillColor: region.color,
                fillOpacity: isActive ? 0.28 : 0.14,
                opacity: isActive ? 0.85 : 0.45,
                weight: isActive ? 2.5 : 1.5,
              }}
              eventHandlers={{
                click: () => onSelectRegion(region.id),
              }}
            />
          );
        })}

        {regions.flatMap((region) => {
          const hubs = HUB_COORDS[region.id] ?? [];
          return hubs.map((hub) => (
            <Marker
              key={`hub-${region.id}-${hub.name}`}
              position={[hub.lat, hub.lng]}
              icon={hubMarkerIcon(region.color)}
              eventHandlers={{
                click: () => onSelectRegion(region.id),
              }}
              title={`${hub.name} — ${region.name}`}
            />
          ));
        })}

        {regions.map((region) => {
          const coords = REGION_COORDS[region.id];
          if (!coords) return null;
          const isActive = activeId === region.id;

          return (
            <Marker
              key={`marker-${region.id}`}
              position={[coords.lat, coords.lng]}
              icon={regionMarkerIcon(region, isActive)}
              zIndexOffset={isActive ? 1000 : 100}
              eventHandlers={{
                click: () => onSelectRegion(region.id),
              }}
            />
          );
        })}
      </MapContainer>
    </div>
  );
}
