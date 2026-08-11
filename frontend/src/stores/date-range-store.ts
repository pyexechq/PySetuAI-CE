import { create } from "zustand";
import { persist } from "zustand/middleware";
import { defaultDateRange, type DateRangePreset, presetToRange } from "@/lib/date-range";

interface DateRangeState {
  from: string;
  to: string;
  setRange: (from: string, to: string) => void;
  setPreset: (preset: DateRangePreset) => void;
}

const initial = defaultDateRange();

export const useDateRangeStore = create<DateRangeState>()(
  persist(
    (set) => ({
      from: initial.from,
      to: initial.to,
      setRange: (from, to) => set({ from, to }),
      setPreset: (preset) => {
        const range = presetToRange(preset);
        set(range);
      },
    }),
    { name: "pysetu-date-range" }
  )
);
