"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, CheckCheck, ShieldAlert, AlertTriangle, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useNotifications } from "@/hooks/use-notifications";
import { useNotificationStore } from "@/stores/notification-store";
import { cn } from "@/lib/utils";

const severityIcon = {
  critical: ShieldAlert,
  warning: AlertTriangle,
  info: Info,
};

const severityClass = {
  critical: "text-red-400",
  warning: "text-amber-400",
  info: "text-blue-400",
};

export function NotificationCenter() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const readIds = useNotificationStore((s) => s.readIds);
  const { notifications, unreadCount, isFetching, markRead, markAllRead } = useNotifications();

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

  function openNotification(id: string) {
    markRead(id);
    setOpen(false);
    router.push("/audit-explorer");
  }

  return (
    <div ref={containerRef} className="relative">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Notifications"
        aria-expanded={open}
        className="relative"
        onClick={() => setOpen((value) => !value)}
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </Button>

      {open && (
        <div className="absolute right-0 top-full z-[100] mt-2 w-96 max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-card shadow-xl">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <p className="text-sm font-semibold">Notifications</p>
              <p className="text-xs text-muted-foreground">
                {isFetching ? "Updating…" : `${unreadCount} unread · polls every 15s`}
              </p>
            </div>
            {notifications.length > 0 && unreadCount > 0 && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 gap-1 text-xs"
                onClick={markAllRead}
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Mark all read
              </Button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">No alerts in the last 7 days</p>
            ) : (
              notifications.map((item) => {
                const Icon = severityIcon[item.severity as keyof typeof severityIcon] ?? Info;
                const isUnread = !readIds.includes(item.id);
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={cn(
                      "flex w-full gap-3 border-b border-border/50 px-4 py-3 text-left transition-colors hover:bg-muted/40",
                      isUnread && "bg-muted/20"
                    )}
                    onClick={() => openNotification(item.id)}
                  >
                    <Icon
                      className={cn(
                        "mt-0.5 h-4 w-4 shrink-0",
                        severityClass[item.severity as keyof typeof severityClass] ?? severityClass.info
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium leading-snug">{item.title}</p>
                        <Badge variant="outline" className="shrink-0 text-[10px] capitalize">
                          {item.category}
                        </Badge>
                      </div>
                      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{item.message}</p>
                      <p className="mt-1 font-mono text-[10px] text-muted-foreground/80">{item.timestamp}</p>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="border-t border-border px-4 py-2">
            <Link
              href="/audit-explorer"
              className="text-xs text-primary hover:underline"
              onClick={() => setOpen(false)}
            >
              View full audit log →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
