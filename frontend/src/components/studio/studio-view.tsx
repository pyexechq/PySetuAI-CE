"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Beaker, Loader2, Plug, ScanSearch, Send, Shield, Sparkles } from "lucide-react";
import { GatewayTester } from "@/components/ai-gateway/gateway-tester";
import { SecurityScanPanel, SecurityScanResults } from "@/components/studio/security-scan-panel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { usePolicyRules } from "@/hooks/use-policies";
import { useMcpServers } from "@/hooks/use-mcp-servers";
import { api } from "@/lib/api";
import { gatewayTestPrompts } from "@/lib/test-prompts";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

const tabs = [
  { id: "prompt", label: "Prompt Lab", icon: Sparkles },
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
  const [preflightPrompt, setPreflightPrompt] = useState(gatewayTestPrompts[0].content);
  const { data: rules = [] } = usePolicyRules();
  const { data: mcpServers = [] } = useMcpServers();
  const [selectedMcp, setSelectedMcp] = useState<string>("");
  const [mcpTool, setMcpTool] = useState("query");
  const [mcpResult, setMcpResult] = useState<string | null>(null);

  const preflightScan = useMutation({
    mutationFn: () => api.scanSecurityContent(token!, { content: preflightPrompt }),
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

      {tab === "prompt" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Beaker className="h-4 w-4" />
            Pre-scan content with the live threat engine, then send through the AI Gateway.
          </div>

          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle className="text-base">Pre-flight security scan</CardTitle>
              <CardDescription>
                Uses <code className="text-xs">POST /security/scan</code> — same rules as the gateway ingress pipeline.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <textarea
                value={preflightPrompt}
                onChange={(e) => setPreflightPrompt(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-ring focus-visible:ring-2"
              />
              <div className="flex flex-wrap gap-2">
                {gatewayTestPrompts.slice(0, 4).map((item) => (
                  <Button
                    key={item.label}
                    variant="outline"
                    size="sm"
                    onClick={() => setPreflightPrompt(item.content)}
                    title={item.description}
                  >
                    {item.label}
                    <Badge variant="outline" className="ml-1 text-[10px] capitalize">
                      {item.expected}
                    </Badge>
                  </Button>
                ))}
              </div>
              <Button
                variant="secondary"
                className="gap-2"
                disabled={!token || !preflightPrompt.trim() || preflightScan.isPending}
                onClick={() => preflightScan.mutate()}
              >
                {preflightScan.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ScanSearch className="h-4 w-4" />
                )}
                Scan before send
              </Button>
              {preflightScan.data && <SecurityScanResults result={preflightScan.data} />}
            </CardContent>
          </Card>

          <GatewayTester />
        </div>
      )}

      {tab === "policy" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle>Policy Dry Run</CardTitle>
              <CardDescription>Live scan via injection detection + DLP threat rules (not client-side regex).</CardDescription>
            </CardHeader>
            <CardContent>
              <SecurityScanPanel
                content={policyInput}
                onContentChange={setPolicyInput}
                presets={policyPresets}
                scanLabel="Evaluate with threat engine"
              />
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
              <CardTitle>Registered Servers</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {mcpServers.map((server) => (
                <div
                  key={server.id}
                  className="flex items-center justify-between rounded-md border border-border/60 p-3 text-sm"
                >
                  <div>
                    <p className="font-medium">{server.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {server.category} · {server.tools} tools · {server.totalCalls.toLocaleString()} calls
                    </p>
                  </div>
                  <Badge
                    variant={
                      server.status === "healthy"
                        ? "success"
                        : server.status === "degraded"
                          ? "warning"
                          : "destructive"
                    }
                  >
                    {server.status}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
