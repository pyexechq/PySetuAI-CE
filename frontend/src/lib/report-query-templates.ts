import type { ApiReportQueryTemplate } from "@/lib/api";

export function resolveReportQueryTemplates(
  templates: ApiReportQueryTemplate[] | undefined
): ApiReportQueryTemplate[] {
  return templates ?? [];
}

export function getQueryTemplateForSource(
  source: string,
  templates: ApiReportQueryTemplate[]
): ApiReportQueryTemplate | undefined {
  return templates.find((t) => t.source === source);
}
