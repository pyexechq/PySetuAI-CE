"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import {
  ArrowRight,
  ArrowRightLeft,
  Beaker,
  ExternalLink,
  Loader2,
  Plug,
  Radar,
  ScanSearch,
  Send,
  Shield,
  Sparkles,
} from "lucide-react";
import { UagTranslationSimulator } from "@/components/studio/uag-translation-simulator";
import { PromptLabTab } from "@/components/studio/prompt-lab-tab";
import { SecurityScanResults } from "@/components/studio/security-scan-panel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { usePolicyRules } from "@/hooks/use-policies";
import { useMcpServers } from "@/hooks/use-mcp-servers";
import { api, type ApiPolicyTestResponse } from "@/lib/api";
import { gatewayTestPrompts } from "@/lib/test-prompts";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

const tabs = [
  { id: "prompt", label: "Prompt Lab", icon: Sparkles },
  { id: "translation", label: "Translation Simulator", icon: ArrowRightLeft },
  { id: "policy", label: "Policy Sandbox", icon: Shield },
  { id: "mcp", label: "MCP Simulator", icon: Plug },
] as const;

type TabId = (typeof tabs)[number]["id"];

const policyPresets = gatewayTestPrompts.map((item) => ({
  label: item.label,
  content: item.content,
}));

export function StudioView() {
  const token = useAuthStore((s) => s.token);
  const [tab, setTab] = useState<TabId>("prompt");
  const [policyInput, setPolicyInput] = useState(gatewayTestPrompts[2].content);
  const { data: rules = [] } = usePolicyRules();
  const { data: mcpServers = [] } = useMcpServers();
  const [selectedMcp, setSelectedMcp] = useState<string>("");
  const [mcpTool, setMcpTool] = useState("query");
  const [mcpResult, setMcpResult] = useState<string | null>(null);
  const [policyTestResult, setPolicyTestResult] = useState<ApiPolicyTestResponse | null>(null);

  const policyTest = useMutation({
    mutationFn: () =>
      api.testPolicyRules(token!, {
        content: policyInput,
        rules: rules.map((r) => ({
          id: r.id,
          name: r.name,
          condition: r.condition,
          action: r.action,
          severity: r.severity,
          enabled: r.enabled,
        })),
      }),
    onSuccess: (data) => setPolicyTestResult(data),
  });

  function simulateMcpCall() {
    const server = mcpServers.find((s) => s.id === selectedMcp);
    if (!server) {
      setMcpResult("Select an MCP server first.");
      return;
    }
    if (server.status === "offline") {
      setMcpResult(`Blocked: ${server.name} is offline. Tool call rejected by MCP Broker.`);
      return;
    }
    setMcpResult(
      `[${server.name}] Tool "${mcpTool}" executed in ${server.avgLatency}ms — success rate ${server.successRate}%. Mock result returned.`
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <Button
            key={id}
            variant={tab === id ? "default" : "outline"}
            onClick={() => setTab(id)}
            className="gap-2"
          >
            <Icon className="h-4 w-4" />
            {label}
          </Button>
        ))}
      </div>

      {tab === "prompt" && <PromptLabTab />}

      {tab === "translation" && <UagTranslationSimulator />}

      {tab === "policy" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle>Policy Dry Run</CardTitle>
              <CardDescription>
                Draft content to evaluate against tenant rules. Run the full threat engine in Monitoring.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <textarea
                value={policyInput}
                onChange={(e) => setPolicyInput(e.target.value)}
                rows={5}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-ring focus-visible:ring-2"
              />
              <div className="flex flex-wrap gap-2">
                {policyPresets.map((item) => (
                  <Button
                    key={item.label}
                    variant="outline"
                    size="sm"
                    onClick={() => setPolicyInput(item.content)}
                  >
                    {item.label}
                  </Button>
                ))}
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  variant="secondary"
                  className="gap-2"
                  disabled={!token || !policyInput.trim() || policyTest.isPending}
                  onClick={() => policyTest.mutate()}
                >
                  {policyTest.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Radar className="h-4 w-4" />
                  )}
                  Evaluate in sandbox
                </Button>
                <Button variant="outline" size="sm" className="gap-2" asChild>
                  <Link href="/monitoring?tab=security">
                    Open Monitoring
                    <ExternalLink className="h-3.5 w-3.5" />
                  </Link>
                </Button>
              </div>

              {policyTest.isError && (
                <p className="text-sm text-destructive">
                  {policyTest.error instanceof Error ? policyTest.error.message : "Policy evaluation failed"}
                </p>
              )}

              {policyTestResult && (
                <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={policyTestResult.allowed ? "success" : "destructive"}>
                      {policyTestResult.allowed ? "Allowed" : "Blocked"}
                    </Badge>
                    <Badge variant="outline">Action: {policyTestResult.action}</Badge>
                    <Badge variant={policyTestResult.risk.toLowerCase() === "high" ? "destructive" : "outline"}>
                      Risk: {policyTestResult.risk}
                    </Badge>
                  </div>
                  {policyTestResult.violations.length > 0 ? (
                    <ul className="mt-3 space-y-2">
                      {policyTestResult.violations.map((v, i) => (
                        <li
                          key={i}
                          className="rounded-md border border-border/50 bg-background/40 px-2 py-1.5 text-xs"
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium">{v.rule_name}</span>
                            <Badge variant="outline">{v.action}</Badge>
                            <Badge variant={v.severity.toLowerCase() === "critical" || v.severity.toLowerCase() === "high" ? "destructive" : "warning"}>
                              {v.severity}
                            </Badge>
                          </div>
                          <p className="mt-1 text-muted-foreground">{v.detail}</p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-xs text-emerald-400">No policy rules matched.</p>
                  )}
                  {policyTestResult.redacted_content && (
                    <div className="mt-3 space-y-1">
                      <p className="text-xs font-medium text-muted-foreground">Redacted preview</p>
                      <pre className="whitespace-pre-wrap rounded-md border border-border/60 bg-background/50 p-2 text-xs font-mono">
                        {policyTestResult.redacted_content}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle>Active Rules ({rules.filter((r) => r.enabled).length})</CardTitle>
              <CardDescription>Tenant policy rules applied at gateway ingress alongside built-in threat detection.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {rules.length === 0 ? (
                <p className="text-sm text-muted-foreground">No custom rules — built-in threat rules still apply.</p>
              ) : (
                rules.map((rule) => (
                  <div
                    key={rule.id}
                    className={cn(
                      "rounded-md border border-border/60 p-3 text-sm",
                      !rule.enabled && "opacity-50"
                    )}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{rule.name}</span>
                      <Badge variant="outline">{rule.action}</Badge>
                      <Badge variant={rule.enabled ? "success" : "secondary"}>
                        {rule.enabled ? "enabled" : "disabled"}
                      </Badge>
                    </div>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">{rule.condition}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {tab === "mcp" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle>MCP Tool Simulator</CardTitle>
              <CardDescription>Mock tool calls against registered servers — inventory lives in MCP Governance.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">MCP Server</label>
                <select
                  value={selectedMcp}
                  onChange={(e) => setSelectedMcp(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none"
                >
                  <option value="">Select server…</option>
                  {mcpServers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.status})
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Tool</label>
                <input
                  value={mcpTool}
                  onChange={(e) => setMcpTool(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none"
                  placeholder="query"
                />
              </div>
              <Button onClick={simulateMcpCall} className="gap-2">
                <Send className="h-4 w-4" />
                Simulate Tool Call
              </Button>
              {mcpResult && (
                <p className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm">{mcpResult}</p>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle>Server inventory</CardTitle>
              <CardDescription>
                Health, tools, and call metrics are maintained in MCP Governance — not duplicated here.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                {mcpServers.length} server{mcpServers.length === 1 ? "" : "s"} available for simulation.
              </p>
              <Button variant="outline" className="gap-2" asChild>
                <Link href="/mcp-governance">
                  <ExternalLink className="h-4 w-4" />
                  Open MCP Governance
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
