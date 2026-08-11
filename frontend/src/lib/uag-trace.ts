export interface UagTranslationTrace {
  source_protocol: string;
  requested_model: string;
  canonical_model: string;
  target_provider: string;
  target_protocol: string;
  translated_model: string;
  governance_actions?: string[];
  translation_ms?: number;
  policy_applied?: string | null;
  compatibility_score?: number | null;
  unsupported_features?: string[];
}

const UAG_TRACE_MARKER = "|uag_trace=";

export function parseUagTraceFromDetails(details: string): {
  summary: string;
  trace: UagTranslationTrace | null;
} {
  const markerIndex = details.indexOf(UAG_TRACE_MARKER);
  if (markerIndex === -1) {
    return { summary: details, trace: null };
  }

  const summary = details.slice(0, markerIndex).trim();
  const payload = details.slice(markerIndex + UAG_TRACE_MARKER.length);
  try {
    return { summary, trace: JSON.parse(payload) as UagTranslationTrace };
  } catch {
    return { summary: details, trace: null };
  }
}
