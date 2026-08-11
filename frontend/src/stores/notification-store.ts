import { create } from "zustand";
import { persist } from "zustand/middleware";

interface NotificationState {
  readIds: string[];
  markRead: (id: string) => void;
  markAllRead: (ids: string[]) => void;
  clearRead: () => void;
}

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      readIds: [],
      markRead: (id) => {
        if (get().readIds.includes(id)) return;
        set({ readIds: [...get().readIds, id] });
      },
      markAllRead: (ids) => {
        const merged = new Set([...get().readIds, ...ids]);
        set({ readIds: Array.from(merged) });
      },
      clearRead: () => set({ readIds: [] }),
    }),
    { name: "pysetu-notifications" }
  )
);
