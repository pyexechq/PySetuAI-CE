"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X, Loader2, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ApiDashboardMetricInsight } from "@/lib/api";

interface MetricInsightModalProps {
  open: boolean;
  loading: boolean;
  insight: ApiDashboardMetricInsight | null;
  error?: string | null;
  pendingTitle?: string | null;
  onClose: () => void;
}

export function MetricInsightModal({
  open,
  loading,
  insight,
  error,
  pendingTitle,
  onClose,
}: MetricInsightModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open || !mounted) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="metric-insight-title"
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 id="metric-insight-title" className="flex items-center gap-2 text-lg font-semibold">
              <Sparkles className="h-5 w-5 text-indigo-400" />
              AI summary & insights
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {insight?.title ?? pendingTitle ?? "Dashboard metric"}
            </p>
          </div>
          <Button variant="outline" size="sm" className="h-8 w-8 p-0" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {loading && (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating insights…
          </div>
        )}

        {!loading && error && <p className="text-sm text-destructive">{error}</p>}

        {!loading && insight && !error && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Badge variant={insight.ai_generated ? "default" : "outline"}>
                {insight.ai_generated ? "AI generated" : "PySetu playbook"}
              </Badge>
            </div>

            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Summary</p>
              <p className="text-sm leading-relaxed text-foreground">{insight.summary}</p>
            </div>

            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Insights</p>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {insight.insights.map((item) => (
                  <li key={item} className="rounded-md border border-border/60 bg-muted/10 px-3 py-2">
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Recommended actions
              </p>
              <ol className="list-decimal space-y-2 pl-5 text-sm text-muted-foreground">
                {insight.recommended_actions.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}
