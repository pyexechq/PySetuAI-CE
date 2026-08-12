import { create } from "zustand";
import { persist } from "zustand/middleware";

interface PreferencesState {
  timezone: string;
  setTimezone: (timezone: string) => void;
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      timezone: "browser",
      setTimezone: (timezone) => set({ timezone }),
    }),
    {
      name: "pysetu-preferences",
    }
  )
);
