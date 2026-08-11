"use client";

import { useEffect, useRef, useState } from "react";
import { Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatDateRangeLabel, type DateRangePreset } from "@/lib/date-range";
import { useDateRangeStore } from "@/stores/date-range-store";

const PRESETS: { id: DateRangePreset; label: string }[] = [
  { id: "last7", label: "Last 7 days" },
  { id: "last30", label: "Last 30 days" },
  { id: "last90", label: "Last 90 days" },
  { id: "thisMonth", label: "This month" },
];

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function DateRangePicker() {
  const { from, to, setRange, setPreset } = useDateRangeStore();
  const [open, setOpen] = useState(false);
  const [draftFrom, setDraftFrom] = useState(from);
  const [draftTo, setDraftTo] = useState(to);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setDraftFrom(from);
      setDraftTo(to);
    }
  }, [open, from, to]);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", onPointerDown);
      return () => document.removeEventListener("mousedown", onPointerDown);
    }
  }, [open]);

  function applyCustomRange() {
    if (!draftFrom || !draftTo || draftFrom > draftTo) return;
    setRange(draftFrom, draftTo);
    setOpen(false);
  }

  function selectPreset(preset: DateRangePreset) {
    setPreset(preset);
    setOpen(false);
  }

  return (
    <div ref={containerRef} className="relative">
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="hidden gap-2 md:flex"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <Calendar className="h-4 w-4" />
        {formatDateRangeLabel(from, to)}
      </Button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-72 rounded-xl border border-border bg-card p-4 shadow-xl">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Quick ranges</p>
          <div className="mb-4 grid grid-cols-2 gap-2">
            {PRESETS.map((preset) => (
              <Button
                key={preset.id}
                type="button"
                variant="outline"
                size="sm"
                className="justify-start text-xs"
                onClick={() => selectPreset(preset.id)}
              >
                {preset.label}
              </Button>
            ))}
          </div>

          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Custom range</p>
          <div className="space-y-2">
            <label className="block space-y-1 text-xs">
              <span className="text-muted-foreground">From</span>
              <input
                type="date"
                className={inputClass}
                value={draftFrom}
                max={draftTo}
                onChange={(e) => setDraftFrom(e.target.value)}
              />
            </label>
            <label className="block space-y-1 text-xs">
              <span className="text-muted-foreground">To</span>
              <input
                type="date"
                className={inputClass}
                value={draftTo}
                min={draftFrom}
                onChange={(e) => setDraftTo(e.target.value)}
              />
            </label>
          </div>

          <Button type="button" size="sm" className="mt-3 w-full" onClick={applyCustomRange}>
            Apply range
          </Button>
        </div>
      )}
    </div>
  );
}
