"use client";

import { useState, useMemo, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { Beaker, Radar, ScanSearch, Loader2, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SecurityScanResults } from "@/components/studio/security-scan-panel";
import { usePromptTemplates } from "@/hooks/use-prompt-templates";
import { useAuthStore } from "@/stores/auth-store";
import { api } from "@/lib/api";
import { gatewayTestPrompts } from "@/lib/test-prompts";

export function PromptLabTab() {
  const token = useAuthStore((s) => s.token);
  const [preflightPrompt, setPreflightPrompt] = useState(gatewayTestPrompts[0].content);
  const { data: templates = [] } = usePromptTemplates();
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [variables, setVariables] = useState<Record<string, string>>({});

  const selectedTemplate = useMemo(
    () => templates.find((t) => t.id === selectedTemplateId),
    [templates, selectedTemplateId]
  );

  const resolvedPrompt = useMemo(() => {
    if (!selectedTemplate?.current_version) return preflightPrompt;
    let result = selectedTemplate.current_version.system_prompt;
    const templateVars = selectedTemplate.current_version.variables || [];
    for (const v of templateVars) {
      const val = variables[v] || "";
      const regex = new RegExp(`\\{\\{\\s*${v}\\s*\\}\\}`, "g");
      result = result.replace(regex, val);
    }
    return result;
  }, [selectedTemplate, preflightPrompt, variables]);

  useEffect(() => {
    if (selectedTemplate) {
      setPreflightPrompt("");
    }
  }, [selectedTemplate]);

  const preflightScan = useMutation({
    mutationFn: () => api.scanSecurityContent(token!, { content: resolvedPrompt }),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Beaker className="h-4 w-4" />
          Pre-scan prompts here, then run live completions on the AI Gateway.
        </div>
        <Button variant="outline" size="sm" className="gap-1.5" asChild>
          <Link href="/monitoring?tab=security">
            <Radar className="h-3.5 w-3.5" />
            Full threat scanner
          </Link>
        </Button>
      </div>

      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="text-base">Pre-flight security scan</CardTitle>
          <CardDescription>
            Test raw prompts or select a Managed Template to preview variable injection before scanning.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Use Prompt Template</label>
            <select
              value={selectedTemplateId}
              onChange={(e) => setSelectedTemplateId(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none"
            >
              <option value="">-- Raw Input (No Template) --</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} {t.alias ? `(${t.alias})` : ""} - v{t.current_version?.version || 1}
                </option>
              ))}
            </select>
          </div>

          {selectedTemplate ? (
            <div className="space-y-4 rounded-md border border-border/60 p-4 bg-background">
              {selectedTemplate.current_version?.variables && selectedTemplate.current_version.variables.length > 0 ? (
                <div className="space-y-3">
                  <h4 className="text-sm font-medium">Template Variables</h4>
                  <div className="grid grid-cols-2 gap-3">
                    {selectedTemplate.current_version.variables.map((v) => (
                      <div key={v} className="space-y-1">
                        <label className="text-xs text-muted-foreground font-mono">{v}</label>
                        <input
                          type="text"
                          value={variables[v] || ""}
                          onChange={(e) => setVariables({ ...variables, [v]: e.target.value })}
                          className="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm outline-none"
                          placeholder="Enter value..."
                        />
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No {"{{var}}"} variables found in this template.</p>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium">Resolved System Prompt</label>
                <div className="min-h-[80px] rounded-md bg-muted p-3 text-sm font-mono whitespace-pre-wrap">
                  {resolvedPrompt || <span className="text-muted-foreground opacity-50">Empty prompt</span>}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                value={preflightPrompt}
                onChange={(e) => setPreflightPrompt(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-ring focus-visible:ring-2"
                placeholder="Enter raw prompt to scan..."
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
            </div>
          )}

          <Button
            variant="secondary"
            className="gap-2"
            disabled={!token || !resolvedPrompt.trim() || preflightScan.isPending}
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

      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <p className="font-medium">Live gateway test</p>
            <p className="text-sm text-muted-foreground">
              Send completions through ingress endpoints with the interactive tester on AI Gateway.
            </p>
          </div>
          <Button className="gap-2" asChild>
            <Link href="/ai-gateway">
              Open AI Gateway
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
