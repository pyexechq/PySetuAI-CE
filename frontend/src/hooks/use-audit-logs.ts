"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuditLogEntry } from "@/lib/mock-data";
import { useAuthStore } from "@/stores/auth-store";
import { useDateRangeStore } from "@/stores/date-range-store";

function mapLog(log: {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  resource: string;
  status: string;
  risk: string;
  details: string;
}): AuditLogEntry {
  return {
    id: log.id,
    timestamp: log.timestamp,
    actor: log.actor,
    action: log.action,
    resource: log.resource,
    status: log.status as AuditLogEntry["status"],
    risk: log.risk as AuditLogEntry["risk"],
    details: log.details,
  };
}

export function useAuditLogs(search?: string, status?: string, live = true) {
  const token = useAuthStore((s) => s.token);
  const from = useDateRangeStore((s) => s.from);
  const to = useDateRangeStore((s) => s.to);
  const knownIdsRef = useRef<Set<string>>(new Set());
  const [recentIds, setRecentIds] = useState<Set<string>>(new Set());

  const query = useQuery({
    queryKey: ["audit-logs", token, search, status, from, to],
    queryFn: () =>
      api
        .getAuditLogs(token!, {
          search,
          status: status === "all" ? undefined : status,
          from_date: from,
          to_date: to,
          limit: 200,
        })
        .then((data) => data.map(mapLog)),
    enabled: Boolean(token),
    staleTime: 0,
    refetchInterval: live ? 3000 : false,
    refetchIntervalInBackground: true,
  });

  useEffect(() => {
    if (!query.data?.length) return;

    const incoming = new Set<string>();
    for (const log of query.data) {
      if (!knownIdsRef.current.has(log.id)) {
        incoming.add(log.id);
      }
    }

    for (const log of query.data) {
      knownIdsRef.current.add(log.id);
    }

    if (incoming.size > 0 && knownIdsRef.current.size > incoming.size) {
      setRecentIds(incoming);
      const timer = window.setTimeout(() => setRecentIds(new Set()), 2500);
      return () => window.clearTimeout(timer);
    }
  }, [query.data]);

  useEffect(() => {
    knownIdsRef.current = new Set();
  }, [search, status, token, from, to]);

  return {
    ...query,
    recentIds,
    isLive: live,
  };
}
