"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  Cable,
  Loader2,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Workflow,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  api,
  type ApiCopilotConnector,
  type ApiCopilotDrift,
  type ApiCopilotInstance,
  type ApiCopilotSummary,
} from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

type Tab = "instances" | "connectors" | "drift";

const TABS: { id: Tab; label: string }[] = [
  { id: "instances", label: "Instances" },
  { id: "connectors", label: "Connectors" },
  { id: "drift", label: "Drift" },
];

function riskVariant(score: number): "default" | "secondary" | "warning" | "destructive" | "success" | "outline" {
  if (score >= 80) return "destructive";
  if (score >= 60) return "warning";
  if (score >= 30) return "secondary";
  return "success";
}

function riskLabel(score: number): string {
  if (score >= 80) return "Critical";
  if (score >= 60) return "High";
  if (score >= 30) return "Medium";
  return "Low";
}

function driftVariant(driftType: string): "default" | "secondary" | "warning" | "destructive" | "success" | "outline" {
  if (driftType === "risk_increase") return "destructive";
  if (driftType === "policy_mismatch") return "warning";
  if (driftType === "new_entity") return "secondary";
  if (driftType === "removed_entity") return "outline";
  return "success";
}

function severityVariant(severity: string): "default" | "secondary" | "warning" | "destructive" | "success" | "outline" {
  if (severity === "critical") return "destructive";
  if (severity === "high") return "warning";
  if (severity === "medium") return "secondary";
  return "success";
}

function CopilotGovernanceViewInner() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>("instances");
  const [syncing, setSyncing] = useState(false);
  const [baselining, setBaselining] = useState(false);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["copilot-summary", token],
    queryFn: () => api.getCopilotSummary(token!),
    enabled: Boolean(token),
  });

  const { data: instances = [], isLoading: instancesLoading } = useQuery({
    queryKey: ["copilot-instances", token],
    queryFn: () => api.getCopilotInstances(token!),
    enabled: Boolean(token),
  });

  const { data: connectors = [], isLoading: connectorsLoading } = useQuery({
    queryKey: ["copilot-connectors", token],
    queryFn: () => api.getCopilotConnectors(token!),
    enabled: Boolean(token),
  });

  const { data: drift = [], isLoading: driftLoading } = useQuery({
    queryKey: ["copilot-drift", token],
    queryFn: () => api.getCopilotDrift(token!),
    enabled: Boolean(token),
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (driftId: string) => api.acknowledgeCopilotDrift(token!, driftId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["copilot-drift"] });
      queryClient.invalidateQueries({ queryKey: ["copilot-summary"] });
    },
  });

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.syncCopilot(token!, { instances: [], connectors: [] });
      queryClient.invalidateQueries({ queryKey: ["copilot-instances"] });
      queryClient.invalidateQueries({ queryKey: ["copilot-connectors"] });
      queryClient.invalidateQueries({ queryKey: ["copilot-drift"] });
      queryClient.invalidateQueries({ queryKey: ["copilot-summary"] });
    } finally {
      setSyncing(false);
    }
  };

  const handleCaptureBaseline = async () => {
    setBaselining(true);
    try {
      await api.captureCopilotBaseline(token!, { name: `baseline-${new Date().toISOString().slice(0, 10)}` });
      queryClient.invalidateQueries({ queryKey: ["copilot-drift"] });
    } finally {
      setBaselining(false);
    }
  };

  const isLoading = summaryLoading || instancesLoading || connectorsLoading || driftLoading;

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading Microsoft Copilot governance...
        </CardContent>
      </Card>
    );
  }

  const s: ApiCopilotSummary = summary ?? {
    instances_total: 0,
    instances_by_type: {},
    connectors_total: 0,
    connectors_by_type: {},
    high_risk_instances: 0,
    high_risk_connectors: 0,
    open_drift: 0,
    by_severity: {},
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          <Card className="border-border/60 bg-card/50">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Bot className="h-3.5 w-3.5" /> Instances
              </div>
              <p className="mt-1 text-2xl font-semibold">{s.instances_total}</p>
            </CardContent>
          </Card>
          <Card className="border-border/60 bg-card/50">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Cable className="h-3.5 w-3.5" /> Connectors
              </div>
              <p className="mt-1 text-2xl font-semibold">{s.connectors_total}</p>
            </CardContent>
          </Card>
          <Card className="border-border/60 bg-card/50">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <ShieldAlert className="h-3.5 w-3.5 text-amber-500" /> High-risk
              </div>
              <p className="mt-1 text-2xl font-semibold">{s.high_risk_instances + s.high_risk_connectors}</p>
            </CardContent>
          </Card>
          <Card className="border-border/60 bg-card/50">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Workflow className="h-3.5 w-3.5 text-amber-500" /> Open drift
              </div>
              <p className="mt-1 text-2xl font-semibold">{s.open_drift}</p>
            </CardContent>
          </Card>
          <Card className="border-border/60 bg-card/50">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" /> Critical drift
              </div>
              <p className="mt-1 text-2xl font-semibold">{s.by_severity.critical ?? 0}</p>
            </CardContent>
          </Card>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleCaptureBaseline} disabled={baselining}>
            {baselining ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            Capture Baseline
          </Button>
          <Button size="sm" onClick={handleSync} disabled={syncing}>
            {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Sync
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {activeTab === "instances" && (
        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              Copilot Instances
            </CardTitle>
            <CardDescription>M365 Copilot, Copilot Studio agents, and Teams.</CardDescription>
          </CardHeader>
          <CardContent>
            {instances.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
                <Bot className="mx-auto h-8 w-8 text-muted-foreground/50" />
                <p className="mt-3 font-medium">No Copilot instances synced</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Sync a tenant payload to populate the inventory.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {instances.map((instance: ApiCopilotInstance) => (
                  <div
                    key={instance.id}
                    className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/50 p-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{instance.name}</p>
                        <Badge variant="outline">{instance.instance_type}</Badge>
                        <Badge variant="outline">{instance.status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {instance.owner ? `Owner: ${instance.owner}` : ""}
                        {instance.environment ? ` · ${instance.environment}` : ""}
                        {instance.data_sources?.length ? ` · ${instance.data_sources.join(", ")}` : ""}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {instance.last_synced_at ? `Synced ${new Date(instance.last_synced_at).toLocaleString()}` : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant={riskVariant(instance.risk_score)}>
                        {riskLabel(instance.risk_score)} · {instance.risk_score}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "connectors" && (
        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cable className="h-5 w-5" />
              Copilot Connectors
            </CardTitle>
            <CardDescription>Power Platform, Graph, and custom connectors with risk assessment.</CardDescription>
          </CardHeader>
          <CardContent>
            {connectors.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
                <Cable className="mx-auto h-8 w-8 text-muted-foreground/50" />
                <p className="mt-3 font-medium">No connectors synced</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Sync a tenant payload to populate the connector inventory.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {connectors.map((connector: ApiCopilotConnector) => (
                  <div
                    key={connector.id}
                    className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/50 p-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{connector.name}</p>
                        <Badge variant="outline">{connector.connector_type}</Badge>
                        <Badge variant="outline">{connector.status}</Badge>
                        {connector.auth_type ? <Badge variant="outline">{connector.auth_type}</Badge> : null}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {connector.publisher ? `Publisher: ${connector.publisher}` : ""}
                        {connector.scopes?.length ? ` · ${connector.scopes.join(", ")}` : ""}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {connector.last_synced_at ? `Synced ${new Date(connector.last_synced_at).toLocaleString()}` : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant={riskVariant(connector.risk_score)}>
                        {riskLabel(connector.risk_score)} · {connector.risk_score}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "drift" && (
        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldX className="h-5 w-5" />
              Governance Drift
            </CardTitle>
            <CardDescription>Changes in risk, status, or inventory since the last baseline.</CardDescription>
          </CardHeader>
          <CardContent>
            {drift.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
                <ShieldCheck className="mx-auto h-8 w-8 text-muted-foreground/50" />
                <p className="mt-3 font-medium">No drift detected</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Capture a baseline and sync to detect governance drift.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {drift.map((record: ApiCopilotDrift) => (
                  <div
                    key={record.id}
                    className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/50 p-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{record.entity_name || record.entity_external_id}</p>
                        <Badge variant={driftVariant(record.drift_type)}>{record.drift_type}</Badge>
                        <Badge variant={severityVariant(record.severity)}>{record.severity}</Badge>
                        <Badge variant="outline">{record.status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{record.description}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {record.created_at ? new Date(record.created_at).toLocaleString() : ""}
                      </p>
                    </div>
                    {record.status === "open" && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => acknowledgeMutation.mutate(record.id)}
                        disabled={acknowledgeMutation.isPending}
                      >
                        Acknowledge
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export function CopilotGovernanceView() {
  return <CopilotGovernanceViewInner />;
}
