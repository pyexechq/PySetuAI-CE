"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Loader2, ShieldOff } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiPolicyExemption } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { formatDateTime } from "@/lib/date-utils";
import { usePreferencesStore } from "@/stores/preferences-store";
import { toast } from "react-hot-toast";

export function PolicyExemptionPanel() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const timezone = usePreferencesStore((s) => s.timezone);
  const queryClient = useQueryClient();
  const canManage = user?.role === "tenant_admin" || user?.role === "security_admin";

  const [reason, setReason] = useState("Legal-approved embedding of redacted HR record for incident review");
  const [ticketRef, setTicketRef] = useState("INC-4521");
  const [durationMinutes, setDurationMinutes] = useState("60");

  const { data: exemptions = [], isLoading } = useQuery({
    queryKey: ["policy-exemptions", token],
    queryFn: () => api.listPolicyExemptions(token!),
    enabled: Boolean(token),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createPolicyExemption(token!, {
        reason,
        ticket_ref: ticketRef || undefined,
        duration_minutes: Number(durationMinutes) || 60,
        max_uses: 1,
        allowed_destinations: ["embedding", "llm"],
      }),
    onSuccess: (row) => {
      queryClient.invalidateQueries({ queryKey: ["policy-exemptions"] });
      toast.success(`Exemption created: ${row.id.slice(0, 8)}…`);
    },
    onError: () => toast.error("Unable to create exemption."),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => api.revokePolicyExemption(token!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy-exemptions"] });
      toast.success("Exemption revoked.");
    },
  });

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldOff className="h-5 w-5" />
          Break-glass exemptions
        </CardTitle>
        <CardDescription>
          Time-bound, audited overrides for embedding hops only. PHI/PCI and vector-store upserts cannot be exempted.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {canManage && (
          <div className="grid gap-3 rounded-lg border border-border/60 p-4 sm:grid-cols-2">
            <div className="space-y-1 sm:col-span-2">
              <label className="text-sm font-medium">Reason</label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={2}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Ticket reference</label>
              <input
                value={ticketRef}
                onChange={(e) => setTicketRef(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Duration (minutes)</label>
              <input
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <Button
              className="gap-2 sm:col-span-2 sm:w-fit"
              disabled={!token || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
              Issue exemption token
            </Button>
          </div>
        )}

        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading exemptions…</p>
        ) : exemptions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No active exemptions. Issue one to pass its ID in governed RAG requests.</p>
        ) : (
          <div className="space-y-2">
            {exemptions.map((row: ApiPolicyExemption) => (
              <div key={row.id} className="rounded-lg border border-border/60 p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <code className="text-xs">{row.id.slice(0, 8)}…</code>
                  <Badge variant="outline">{row.status}</Badge>
                  <span className="text-xs text-muted-foreground">
                    expires {formatDateTime(row.expires_at, timezone)}
                  </span>
                </div>
                <p className="mt-1 text-muted-foreground">{row.reason}</p>
                <p className="text-xs text-muted-foreground">
                  Destinations: {row.allowed_destinations.join(", ")} · uses {row.use_count}
                  {row.max_uses ? `/${row.max_uses}` : ""}
                </p>
                {canManage && row.status === "active" && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    disabled={revokeMutation.isPending}
                    onClick={() => revokeMutation.mutate(row.id)}
                  >
                    Revoke
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
