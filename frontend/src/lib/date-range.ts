export type DateRangePreset = "last7" | "last30" | "last90" | "thisMonth";

export interface DateRange {
  from: string;
  to: string;
}

function pad(n: number) {
  return String(n).padStart(2, "0");
}

export function toIsoDate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function parseIsoDate(value: string): Date {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function formatDateRangeLabel(from: string, to: string): string {
  const start = parseIsoDate(from);
  const end = parseIsoDate(to);
  const sameYear = start.getFullYear() === end.getFullYear();
  const startFmt = start.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    ...(sameYear ? {} : { year: "numeric" }),
  });
  const endFmt = end.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return `${startFmt} – ${endFmt}`;
}

export function presetToRange(preset: DateRangePreset): DateRange {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const to = toIsoDate(today);

  if (preset === "thisMonth") {
    const start = new Date(today.getFullYear(), today.getMonth(), 1);
    return { from: toIsoDate(start), to };
  }

  const days = preset === "last7" ? 6 : preset === "last30" ? 29 : 89;
  const start = new Date(today);
  start.setDate(start.getDate() - days);
  return { from: toIsoDate(start), to };
}

export function defaultDateRange(): DateRange {
  return presetToRange("last7");
}
