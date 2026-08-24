"use client";

import { useEffect, useRef, useState } from "react";
import { keepPreviousData, useQuery, useInfiniteQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuditLogEntry } from "@/lib/mock-data";
import { useAuthStore } from "@/stores/auth-store";
import { useDateRangeStore } from "@/stores/date-range-store";

function mapLog(log: {
  id: string;
  timestamp: string;
  source: string;
  actor: string;
  action: string;
  resource: string;
  status: string;
  risk: string;
  details: string;
  has_request_log?: boolean;
  matched_routing_rule?: string | null;
  routing_strategy?: string | null;
  upstream?: string | null;
}): AuditLogEntry {
  return {
    id: log.id,
    timestamp: log.timestamp,
    source: log.source,
    actor: log.actor,
    action: log.action,
    resource: log.resource,
    status: log.status as AuditLogEntry["status"],
    risk: log.risk as AuditLogEntry["risk"],
    details: log.details,
    has_request_log: log.has_request_log ?? false,
    matched_routing_rule: log.matched_routing_rule ?? null,
    routing_strategy: log.routing_strategy ?? null,
    upstream: log.upstream ?? null,
  };
}

export function useAuditLogs(search?: string, status?: string, live = true, auditId?: string, source?: string) {
  const token = useAuthStore((s) => s.token);
  const from = useDateRangeStore((s) => s.from);
  const to = useDateRangeStore((s) => s.to);
  const knownIdsRef = useRef<Set<string>>(new Set());
  const [recentIds, setRecentIds] = useState<Set<string>>(new Set());
  const [debouncedSearch, setDebouncedSearch] = useState(search);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const query = useInfiniteQuery({
    queryKey: ["audit-logs", token, debouncedSearch, status, auditId, source, from, to],
    initialPageParam: 0,
    queryFn: ({ pageParam = 0 }) =>
      api
        .getAuditLogs(token!, {
          search: auditId ? undefined : debouncedSearch,
          audit_id: auditId,
          status: status === "all" ? undefined : status,
          source: source === "all" ? undefined : source,
          from_date: from,
          to_date: to,
          limit: 200,
          offset: pageParam,
        })
        .then((data) => data.map(mapLog)),
    getNextPageParam: (lastPage, allPages) => {
      return lastPage.length === 200 ? allPages.length * 200 : undefined;
    },
    enabled: Boolean(token),
    placeholderData: keepPreviousData,
    staleTime: 1_000,
    refetchInterval: (q) => (live && q.state.data?.pages.length === 1 ? 3000 : false),
    refetchIntervalInBackground: true,
  });

  const flatData = query.data?.pages.flat() ?? [];

  useEffect(() => {
    if (!flatData.length) return;

    const incoming = new Set<string>();
    for (const log of flatData) {
      if (!knownIdsRef.current.has(log.id)) {
        incoming.add(log.id);
      }
    }

    for (const log of flatData) {
      knownIdsRef.current.add(log.id);
    }

    if (incoming.size > 0 && knownIdsRef.current.size > incoming.size) {
      setRecentIds(incoming);
      const timer = window.setTimeout(() => setRecentIds(new Set()), 2500);
      return () => window.clearTimeout(timer);
    }
  }, [flatData]);

  useEffect(() => {
    knownIdsRef.current = new Set();
  }, [debouncedSearch, status, auditId, source, token, from, to]);

  return {
    ...query,
    data: flatData,
    recentIds,
    isLive: live,
  };
}

export function useAuditSummary(search?: string, status?: string, auditId?: string, source?: string) {
  const token = useAuthStore((s) => s.token);
  const from = useDateRangeStore((s) => s.from);
  const to = useDateRangeStore((s) => s.to);
  const [debouncedSearch, setDebouncedSearch] = useState(search);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  return useQuery({
    queryKey: ["audit-summary", token, debouncedSearch, status, auditId, source, from, to],
    queryFn: () =>
      api.getAuditSummary(token!, {
        search: auditId ? undefined : debouncedSearch,
        audit_id: auditId,
        status: status === "all" ? undefined : status,
        source: source === "all" ? undefined : source,
        from_date: from,
        to_date: to,
      }),
    enabled: Boolean(token),
    placeholderData: keepPreviousData,
    staleTime: 5_000,
  });
}
