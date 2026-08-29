"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Cable,
  Loader2,
  Play,
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
  type ApiAgentAnomaly,
  type ApiExfiltrationEvent,
  type ApiGuardianAction,
  type ApiPromptInjectionFinding,
} from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

type Tab = "anomalies" | "prompt-injection" | "exfiltration" | "guardian";

const TABS: { id: Tab; label: string }[] = [
  { id: "anomalies", label: "Anomalies" },
  { id: "prompt-injection", label: "Prompt Injection" },
  { id: "exfiltration", label: "Exfiltration" },
  { id: "guardian", label: "Guardian" },
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

function severityVariant(severity: string): "default" | "secondary" | "warning" | "destructive" | "success" | "outline" {
  if (severity === "critical") return "destructive";
  if (severity === "high") return "warning";
  if (severity === "medium") return "secondary";
  return "success";
}

function statusVariant(status: string): "default" | "secondary" | "warning" | "destructive" | "success" | "outline" {
  if (status === "open" || status === "pending") return "warning";
  if (status === "executed") return "success";
  if (status === "failed") return "destructive";
  return "secondary";
}

function AgenticSecurityViewInner() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>("anomalies");
  const [guardianRunning, setGuardianRunning] = useState(false);

  const { data: anomalySummary, isLoading: anomalySummaryLoading } = useQuery({
    queryKey: ["agentic-anomaly-summary", token],
    queryFn: () => api.getAgentAnomalySummary(token!),
    enabled: Boolean(token),
  });
  const { data: injectionSummary, isLoading: injectionSummaryLoading } = useQuery({
    queryKey: ["agentic-injection-summary", token],
    queryFn: () => api.getPromptInjectionSummary(token!),
    enabled: Boolean(token),
  });
  const { data: exfilSummary, isLoading: exfilSummaryLoading } = useQuery({
    queryKey: ["agentic-exfil-summary", token],
    queryFn: () => api.getExfiltrationSummary(token!),
    enabled: Boolean(token),
  });
  const { data: guardianSummary, isLoading: guardianSummaryLoading } = useQuery({
    queryKey: ["agentic-guardian-summary", token],
    queryFn: () => api.getGuardianSummary(token!),
    enabled: Boolean(token),
  });

  const { data: anomalies = [], isLoading: anomaliesLoading } = useQuery({
    queryKey: ["agentic-anomalies", token],
    queryFn: () => api.getAgentAnomalies(token!),
    enabled: Boolean(token),
  });
  const { data: findings = [], isLoading: findingsLoading } = useQuery({
    queryKey: ["agentic-findings", token],
    queryFn: () => api.getPromptInjectionFindings(token!),
    enabled: Boolean(token),
  });
  const { data: exfilEvents = [], isLoading: exfilEventsLoading } = useQuery({
    queryKey: ["agentic-exfil", token],
    queryFn: () => api.getExfiltrationEvents(token!),
    enabled: Boolean(token),
  });
  const { data: guardianActions = [], isLoading: guardianActionsLoading } = useQuery({
    queryKey: ["agentic-guardian", token],
    queryFn: () => api.getGuardianActions(token!),
    enabled: Boolean(token),
  });

  const acknowledgeAnomaly = useMutation({
    mutationFn: (id: string) => api.acknowledgeAgentAnomaly(token!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agentic-anomalies"] });
      queryClient.invalidateQueries({ queryKey: ["agentic-anomaly-summary"] });
    },
  });
  const acknowledgeFinding = useMutation({
    mutationFn: (id: string) => api.acknowledgePromptInjection(token!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agentic-findings"] });
      queryClient.invalidateQueries({ queryKey: ["agentic-injection-summary"] });
    },
  });
  const acknowledgeExfil = useMutation({
    mutationFn: (id: string) => api.acknowledgeExfiltration(token!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agentic-exfil"] });
      queryClient.invalidateQueries({ queryKey: ["agentic-exfil-summary"] });
    },
  });
  const executeAction = useMutation({
    mutationFn: (id: string) => api.executeGuardianAction(token!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agentic-guardian"] });
      queryClient.invalidateQueries({ queryKey: ["agentic-guardian-summary"] });
    },
  });

  const handleRunGuardian = async () => {
    setGuardianRunning(true);
    try {
      await api.runGuardianLoop(token!);
      queryClient.invalidateQueries({ queryKey: ["agentic-guardian"] });
      queryClient.invalidateQueries({ queryKey: ["agentic-guardian-summary"] });
      queryClient.invalidateQueries({ queryKey: ["agentic-anomalies"] });
      queryClient.invalidateQueries({ queryKey: ["agentic-findings"] });
      queryClient.invalidateQueries({ queryKey: ["agentic-exfil"] });
    } finally {
      setGuardianRunning(false);
    }
  };

  const isLoading =
    anomalySummaryLoading ||
    injectionSummaryLoading ||
    exfilSummaryLoading ||
    guardianSummaryLoading ||
    anomaliesLoading ||
    findingsLoading ||
    exfilEventsLoading ||
    guardianActionsLoading;

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading agentic security...
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-4 sm:p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-rose-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between w-full min-w-0">
          <div className="space-y-2.5 w-full min-w-0 max-w-xl">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Autonomous Guardian Active
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <ShieldAlert className="h-3.5 w-3.5 text-primary" />
                Rogue Agent Circuit Breaker
              </Badge>
              <Badge variant="outline" className="bg-muted text-muted-foreground border-border/60 text-xs font-mono">
                Sub-2ms Anomaly Trap
              </Badge>
            </div>

            <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-foreground break-words">
              Agentic Threat Defense & Guardian Mesh
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Detect and remediate autonomous agent runaway loops, prompt injection payloads, silent data exfiltration vectors, and unapproved tool call chains.
            </p>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-2.5 sm:gap-3 w-full lg:w-auto shrink-0">
            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Open Anomalies</span>
                <Activity className="h-3.5 w-3.5 text-primary" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-foreground">{anomalySummary?.open ?? 0}</p>
              <p className="text-[10px] text-muted-foreground">Behavioral drifts</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Injections</span>
                <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-amber-600 dark:text-amber-400">{injectionSummary?.open ?? 0}</p>
              <p className="text-[10px] text-muted-foreground">Blocked findings</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Exfiltrations</span>
                <Cable className="h-3.5 w-3.5 text-rose-500" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-rose-600 dark:text-rose-400">{exfilSummary?.open ?? 0}</p>
              <p className="text-[10px] text-muted-foreground">Egress traps</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Guardian Actions</span>
                <Workflow className="h-3.5 w-3.5 text-blue-500" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-blue-600 dark:text-blue-400">{guardianSummary?.pending ?? 0}</p>
              <p className="text-[10px] text-muted-foreground">Pending mitigation</p>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Navigation Action Bar ────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                activeTab === tab.id
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <Button size="sm" className="gap-1.5 text-xs h-8" onClick={handleRunGuardian} disabled={guardianRunning}>
          {guardianRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
          Run Guardian Loop
        </Button>
      </div>

      {activeTab === "anomalies" && (
        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Agent Anomalies
            </CardTitle>
            <CardDescription>Unusual tool usage, data access, volume, timing, and chain risk.</CardDescription>
          </CardHeader>
          <CardContent>
            {anomalies.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
                <ShieldCheck className="mx-auto h-8 w-8 text-muted-foreground/50" />
                <p className="mt-3 font-medium">No anomalies detected</p>
              </div>
            ) : (
              <div className="space-y-3">
                {anomalies.map((anomaly: ApiAgentAnomaly) => (
                  <div
                    key={anomaly.id}
                    className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/50 p-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{anomaly.anomaly_type}</p>
                        <Badge variant={severityVariant(anomaly.severity)}>{anomaly.severity}</Badge>
                        <Badge variant={statusVariant(anomaly.status)}>{anomaly.status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{anomaly.description}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {anomaly.created_at ? new Date(anomaly.created_at).toLocaleString() : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant={riskVariant(anomaly.risk_score)}>
                        {riskLabel(anomaly.risk_score)} · {anomaly.risk_score}
                      </Badge>
                      {anomaly.status === "open" && (
                        <Button variant="outline" size="sm" onClick={() => acknowledgeAnomaly.mutate(anomaly.id)}>
                          Acknowledge
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "prompt-injection" && (
        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5" />
              Prompt Injection Findings
            </CardTitle>
            <CardDescription>Injection patterns detected in files, repos, and MCP resources.</CardDescription>
          </CardHeader>
          <CardContent>
            {findings.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
                <ShieldCheck className="mx-auto h-8 w-8 text-muted-foreground/50" />
                <p className="mt-3 font-medium">No prompt-injection findings</p>
              </div>
            ) : (
              <div className="space-y-3">
                {findings.map((finding: ApiPromptInjectionFinding) => (
                  <div
                    key={finding.id}
                    className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/50 p-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{finding.scan_target}</p>
                        <Badge variant="outline">{finding.scan_target_type}</Badge>
                        <Badge variant={severityVariant(finding.highest_severity)}>{finding.highest_severity}</Badge>
                        <Badge variant={statusVariant(finding.status)}>{finding.status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{finding.content_preview}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {finding.created_at ? new Date(finding.created_at).toLocaleString() : ""}
                      </p>
                    </div>
                    {finding.status === "open" && (
                      <Button variant="outline" size="sm" onClick={() => acknowledgeFinding.mutate(finding.id)}>
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

      {activeTab === "exfiltration" && (
        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cable className="h-5 w-5" />
              Exfiltration Events
            </CardTitle>
            <CardDescription>Large reads, rapid reads, and sensitive data leaving the boundary.</CardDescription>
          </CardHeader>
          <CardContent>
            {exfilEvents.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
                <ShieldCheck className="mx-auto h-8 w-8 text-muted-foreground/50" />
                <p className="mt-3 font-medium">No exfiltration events</p>
              </div>
            ) : (
              <div className="space-y-3">
                {exfilEvents.map((event: ApiExfiltrationEvent) => (
                  <div
                    key={event.id}
                    className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/50 p-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{event.exfil_type}</p>
                        <Badge variant="outline">{event.resource}</Badge>
                        {event.sensitivity ? <Badge variant="outline">{event.sensitivity}</Badge> : null}
                        <Badge variant={statusVariant(event.status)}>{event.status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {event.bytes_read ? `${(event.bytes_read / 1024 / 1024).toFixed(1)} MB` : ""}
                        {event.event_count ? ` · ${event.event_count} events` : ""}
                        {event.window_seconds ? ` · ${event.window_seconds}s` : ""}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {event.created_at ? new Date(event.created_at).toLocaleString() : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant={riskVariant(event.risk_score)}>
                        {riskLabel(event.risk_score)} · {event.risk_score}
                      </Badge>
                      {event.status === "open" && (
                        <Button variant="outline" size="sm" onClick={() => acknowledgeExfil.mutate(event.id)}>
                          Acknowledge
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "guardian" && (
        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Workflow className="h-5 w-5" />
              Guardian Actions
            </CardTitle>
            <CardDescription>Automated remediation actions from the enforcement loop.</CardDescription>
          </CardHeader>
          <CardContent>
            {guardianActions.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
                <ShieldX className="mx-auto h-8 w-8 text-muted-foreground/50" />
                <p className="mt-3 font-medium">No guardian actions</p>
                <p className="mt-1 text-sm text-muted-foreground">Run the Guardian loop to evaluate agent behavior.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {guardianActions.map((action: ApiGuardianAction) => (
                  <div
                    key={action.id}
                    className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/50 p-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{action.action_type}</p>
                        <Badge variant="outline">{action.trigger_type}</Badge>
                        <Badge variant={severityVariant(action.severity)}>{action.severity}</Badge>
                        <Badge variant={statusVariant(action.action_status)}>{action.action_status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{action.details}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {action.created_at ? new Date(action.created_at).toLocaleString() : ""}
                      </p>
                    </div>
                    {action.action_status === "pending" && (
                      <Button variant="outline" size="sm" onClick={() => executeAction.mutate(action.id)}>
                        Execute
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

export function AgenticSecurityView() {
  return <AgenticSecurityViewInner />;
}
