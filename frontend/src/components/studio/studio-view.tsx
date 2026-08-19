"use client";

import { useEffect, useMemo, useState } from "react";
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
import { useClientApiKeys } from "@/hooks/use-client-api-keys";
import { useMcpServers } from "@/hooks/use-mcp-servers";
import {
  api,
  type ApiPolicyPolicyRuleEvaluationResult,
  type ApiPolicyTestResponse,
} from "@/lib/api";
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
  const [debouncedInput, setDebouncedInput] = useState(policyInput);
  const [selectedApiKeyId, setSelectedApiKeyId] = useState<string>("");
  const { data: apiKeys = [], isLoading: apiKeysLoading } = useClientApiKeys();
  const selectedKey = useMemo(
    () => apiKeys.find((k) => k.id === selectedApiKeyId),
    [apiKeys, selectedApiKeyId]
  );
  const rulesBundleId = selectedKey?.bundle_id ?? undefined;
  const rulesDefaultBundle = selectedKey && !selectedKey.bundle_id ? true : undefined;
  const { data: rules = [], isLoading: rulesLoading } = usePolicyRules(
    undefined,
    rulesBundleId,
    rulesDefaultBundle
  );
  const { data: mcpServers = [] } = useMcpServers();
  const [selectedMcp, setSelectedMcp] = useState<string>("");
  const [mcpTool, setMcpTool] = useState("query");
  const [mcpResult, setMcpResult] = useState<string | null>(null);
  const [policyTestResult, setPolicyTestResult] = useState<ApiPolicyTestResponse | null>(null);

  const ruleResultMap = useMemo(() => {
    const map = new Map<string, ApiPolicyPolicyRuleEvaluationResult>();
    policyTestResult?.rule_results?.forEach((r) => {
      if (r.rule_id) map.set(r.rule_id, r);
    });
    return map;
  }, [policyTestResult]);

  const totalRules = rules.filter((r) => r.enabled).length;
  const matchedRules = useMemo(
    () => rules.filter((r) => r.enabled && ruleResultMap.get(r.id)?.matched).length,
    [rules, ruleResultMap]
  );

  useEffect(() => {
    const handle = setTimeout(() => setDebouncedInput(policyInput), 300);
    return () => clearTimeout(handle);
  }, [policyInput]);

  const policyTest = useMutation({
    mutationFn: () =>
      api.testPolicyRules(token!, {
        content: debouncedInput,
        api_key_id: selectedKey!.id,
      }),
    onSuccess: (data) => setPolicyTestResult(data),
  });

  useEffect(() => {
    if (!token || !selectedKey || !debouncedInput.trim()) return;
    policyTest.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedInput, selectedKey?.id, token]);

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
                Select an API key to evaluate against its attached policy bundle in real time.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">API Key</label>
                <select
                  value={selectedApiKeyId}
                  onChange={(e) => setSelectedApiKeyId(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="">{apiKeysLoading ? "Loading keys..." : "Select an API key..."}</option>
                  {apiKeys.map((key) => (
                    <option key={key.id} value={key.id}>
                      {key.name} ({key.key_masked}){key.bundle_name ? ` — ${key.bundle_name}` : ""}
                    </option>
                  ))}
                </select>
              </div>
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
                  disabled={!token || !selectedKey || !policyInput.trim() || policyTest.isPending}
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

              {(policyTest.isPending || policyTestResult) && (
                <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    {policyTest.isPending ? (
                      <Badge variant="outline" className="gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Evaluating
                      </Badge>
                    ) : (
                      <>
                        <Badge variant={policyTestResult!.allowed ? "success" : "destructive"}>
                          {policyTestResult!.allowed ? "Allowed" : "Blocked"}
                        </Badge>
                        <Badge variant="outline">Action: {policyTestResult!.action}</Badge>
                        <Badge variant={policyTestResult!.risk.toLowerCase() === "high" ? "destructive" : "outline"}>
                          Risk: {policyTestResult!.risk}
                        </Badge>
                      </>
                    )}
                  </div>

                  {totalRules > 0 && (
                    <div className="mt-3 space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">
                          {policyTest.isPending ? "Evaluating rules..." : `${matchedRules} of ${totalRules} active rules triggered`}
                        </span>
                        {!policyTest.isPending && (
                          <span className="text-muted-foreground">{Math.round((matchedRules / totalRules) * 100)}%</span>
                        )}
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className={cn(
                            "h-full transition-all",
                            policyTest.isPending ? "bg-primary animate-pulse" : matchedRules > 0 ? "bg-amber-500" : "bg-emerald-500"
                          )}
                          style={{
                            width: policyTest.isPending ? "60%" : `${Math.round((matchedRules / totalRules) * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {!policyTest.isPending && policyTestResult!.violations.length > 0 ? (
                    <ul className="mt-3 space-y-2">
                      {policyTestResult!.violations.map((v, i) => (
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
                    !policyTest.isPending && <p className="mt-2 text-xs text-emerald-400">No policy rules matched.</p>
                  )}

                  {!policyTest.isPending && policyTestResult!.redacted_content && (
                    <div className="mt-3 space-y-1">
                      <p className="text-xs font-medium text-muted-foreground">Redacted preview</p>
                      <pre className="whitespace-pre-wrap rounded-md border border-border/60 bg-background/50 p-2 text-xs font-mono">
                        {policyTestResult!.redacted_content}
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
              <CardDescription>
                {selectedKey
                  ? `Rules from the policy bundle attached to ${selectedKey.name}. Evaluated in real time as you type.`
                  : "Select an API key to view the rules from its attached policy bundle."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {!selectedKey ? (
                <p className="text-sm text-muted-foreground">No API key selected.</p>
              ) : rulesLoading ? (
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading rules...
                </p>
              ) : rules.length === 0 ? (
                <p className="text-sm text-muted-foreground">No custom rules in this bundle — built-in threat rules still apply.</p>
              ) : (
                rules.map((rule) => {
                  const result = ruleResultMap.get(rule.id);
                  const matched = Boolean(result?.matched);
                  return (
                    <div
                      key={rule.id}
                      className={cn(
                        "rounded-md border p-3 text-sm transition-colors",
                        !rule.enabled && "border-slate-500/30 bg-slate-500/5 opacity-50",
                        rule.enabled && !result && "border-border/60",
                        rule.enabled && result && !matched && "border-emerald-500/40 bg-emerald-500/5",
                        rule.enabled && matched && rule.action === "Block" && "border-red-500/60 bg-red-500/10",
                        rule.enabled && matched && rule.action === "Redact" && "border-amber-500/60 bg-amber-500/10",
                        rule.enabled && matched && rule.action === "Alert" && "border-blue-500/60 bg-blue-500/10",
                        rule.enabled && matched && !["Block", "Redact", "Alert"].includes(rule.action) && "border-emerald-500/60 bg-emerald-500/10"
                      )}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{rule.name}</span>
                        <Badge variant="outline">{rule.action}</Badge>
                        <Badge variant={rule.enabled ? "success" : "secondary"}>
                          {rule.enabled ? "enabled" : "disabled"}
                        </Badge>
                        {result && matched && (
                          <Badge variant={rule.action === "Block" ? "destructive" : rule.action === "Redact" ? "warning" : "default"}>
                            Matched
                          </Badge>
                        )}
                        {result && !matched && rule.enabled && (
                          <Badge variant="success">Passed</Badge>
                        )}
                      </div>
                      <p className="mt-1 font-mono text-xs text-muted-foreground">{rule.condition}</p>
                    </div>
                  );
                })
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
