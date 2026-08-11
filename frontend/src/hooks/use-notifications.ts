"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useNotificationStore } from "@/stores/notification-store";

export function useNotifications() {
  const token = useAuthStore((s) => s.token);
  const readIds = useNotificationStore((s) => s.readIds);
  const markRead = useNotificationStore((s) => s.markRead);
  const markAllRead = useNotificationStore((s) => s.markAllRead);

  const query = useQuery({
    queryKey: ["notifications", token, readIds.join(",")],
    queryFn: async () => {
      if (!token) return { notifications: [], unread_count: 0 };
      return api.getNotifications(token, readIds);
    },
    enabled: Boolean(token),
    refetchInterval: 15_000,
    refetchIntervalInBackground: true,
    staleTime: 0,
  });

  const notifications = query.data?.notifications ?? [];
  const unreadCount = notifications.filter((n) => !readIds.includes(n.id)).length;

  return {
    notifications,
    unreadCount,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    markRead,
    markAllRead: () => markAllRead(notifications.map((n) => n.id)),
    refetch: query.refetch,
  };
}
