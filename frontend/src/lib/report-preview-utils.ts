import type { ApiReportPreviewResponse } from "@/lib/api";

export function buildReportSparkline(rowCount: number, seed: string): number[] {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash << 5) - hash + seed.charCodeAt(i);
    hash |= 0;
  }
  const base = Math.max(3, Math.round(rowCount / 7) || 4);
  return Array.from({ length: 7 }, (_, index) => Math.max(1, base + ((hash >> index) % 5) - 2));
}

function isNumeric(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function columnIndex(columns: string[], names: string[]): number {
  const lower = columns.map((c) => c.toLowerCase());
  for (const name of names) {
    const idx = lower.indexOf(name.toLowerCase());
    if (idx >= 0) return idx;
  }
  return -1;
}

export function extractReportChartData(preview: ApiReportPreviewResponse) {
  const { columns, rows } = preview;

  const numericIdx = columns.findIndex((_, colIdx) =>
    rows.some((row) => isNumeric(row[colIdx]))
  );
  if (numericIdx >= 0) {
    const labelIdx = columns.findIndex((_, colIdx) => colIdx !== numericIdx && typeof rows[0]?.[colIdx] === "string");
    const barData = rows.slice(0, 8).map((row, index) => ({
      label: String(labelIdx >= 0 ? row[labelIdx] : `Row ${index + 1}`).slice(0, 18),
      value: isNumeric(row[numericIdx]) ? row[numericIdx] : 0,
    }));
    return { type: "bar" as const, barData };
  }

  const statusIdx = columnIndex(columns, ["status", "risk", "category"]);
  if (statusIdx >= 0) {
    const counts = new Map<string, number>();
    for (const row of rows) {
      const key = String(row[statusIdx] ?? "unknown");
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    const pieData = Array.from(counts.entries())
      .slice(0, 6)
      .map(([name, value]) => ({ name, value }));
    if (pieData.length > 0) {
      return { type: "pie" as const, pieData };
    }
  }

  return { type: "none" as const };
}

export function extractReportKpis(preview: ApiReportPreviewResponse) {
  const { columns, rows, row_count } = preview;
  const kpis: { label: string; value: string }[] = [{ label: "Total rows", value: row_count.toLocaleString() }];

  const blockedIdx = columnIndex(columns, ["status"]);
  if (blockedIdx >= 0) {
    const blocked = rows.filter((row) => String(row[blockedIdx]).toLowerCase() === "blocked").length;
    if (blocked > 0) {
      kpis.push({ label: "Blocked", value: blocked.toLocaleString() });
    }
  }

  const riskIdx = columnIndex(columns, ["risk"]);
  if (riskIdx >= 0) {
    const high = rows.filter((row) => String(row[riskIdx]).toLowerCase() === "high").length;
    if (high > 0) {
      kpis.push({ label: "High risk", value: high.toLocaleString() });
    }
  }

  const requestsIdx = columnIndex(columns, ["total_requests", "total_calls"]);
  if (requestsIdx >= 0) {
    const total = rows.reduce((sum, row) => sum + (isNumeric(row[requestsIdx]) ? row[requestsIdx] : 0), 0);
    if (total > 0) {
      kpis.push({ label: "Volume", value: total.toLocaleString() });
    }
  }

  return kpis.slice(0, 4);
}
