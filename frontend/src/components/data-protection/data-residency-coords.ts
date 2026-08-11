/** Primary region centers for map focus and coverage circles. */
export const WORLD_CENTER = { lat: 25, lng: 10 };
export const WORLD_ZOOM = 2;

export const REGION_COORDS: Record<string, { lat: number; lng: number; zoom: number }> = {
  us: { lat: 38.9, lng: -77.0, zoom: 4 },
  eu: { lat: 50.1, lng: 8.7, zoom: 4 },
  apac: { lat: 1.35, lng: 103.8, zoom: 4 },
};

/** Individual hub cities per region. */
export const HUB_COORDS: Record<string, { name: string; lat: number; lng: number }[]> = {
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

export function circleRadiusMeters(percentage: number) {
  return percentage * 35_000;
}
