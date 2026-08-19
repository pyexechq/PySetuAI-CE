"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Send, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ApiError, api, type ChatCompletionResponse } from "@/lib/api";
import { gatewayTestPrompts } from "@/lib/test-prompts";
import { useAuthStore } from "@/stores/auth-store";

const testPrompts = gatewayTestPrompts;

export function GatewayTester() {
  const token = useAuthStore((s) => s.token);
  const [prompt, setPrompt] = useState(testPrompts[0].content);
  const [model, setModel] = useState("auto");
  const [clientApiKey, setClientApiKey] = useState("");
  const [routingContextJson, setRoutingContextJson] = useState('{"task":{"type":"code_review"}}');
  const [useStream, setUseStream] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<string | null>(null);
  const [meta, setMeta] = useState<ChatCompletionResponse["pysetu"] | null>(null);

  const { data: ollamaStatus } = useQuery({
    queryKey: ["ollama-status", token],
    queryFn: async () => {
      if (!token) return null;
      try {
        return await api.getOllamaStatus(token);
      } catch {
        return null;
      }
    },
    enabled: !!token,
    refetchInterval: 30_000,
  });

  async function runTest() {
    const authToken = clientApiKey.trim() || token;
    if (!authToken) return;
    setLoading(true);
    setResponse(null);
    setBlocked(null);
    setMeta(null);
    try {
      let routing_context: Record<string, unknown> | undefined;
      if (routingContextJson.trim()) {
        routing_context = JSON.parse(routingContextJson) as Record<string, unknown>;
      }
      const payload = {
        model,
        messages: [{ role: "user", content: prompt }],
        ...(routing_context ? { routing_context } : {}),
      };
      if (useStream) {
        let streamed = "";
        await api.chatCompletionStream(authToken, payload, (chunk) => {
          streamed += chunk;
          setResponse(streamed);
        });
        setMeta({ upstream: "stream", inspection_action: "allow" });
      } else {
        const result = await api.chatCompletion(authToken, { ...payload, debug: debugMode });
        setResponse(result.choices[0]?.message?.content ?? "No content");
        setMeta(result.pysetu ?? null);
      }
    } catch (err) {
      if (err instanceof SyntaxError) {
        setBlocked("Routing context must be valid JSON");
      } else if (err instanceof ApiError) {
        if (err.status === 403) {
          setBlocked(`Policy blocked: ${err.message || "Request blocked by PySetu policy engine"}`);
        } else if (err.status === 401) {
          setBlocked("Authentication failed — check your session or client API key");
        } else if (err.status >= 500) {
          setBlocked(`Gateway server error (${err.status}): ${err.message || "Try again shortly"}`);
        } else {
          setBlocked(err.message || `Gateway error (${err.status})`);
        }
      } else if (err instanceof TypeError) {
        setBlocked("Cannot reach gateway — ensure the backend is running and NEXT_PUBLIC_API_URL is correct");
      } else if (err instanceof Error) {
        setBlocked(err.message);
      } else {
        setBlocked("Gateway request failed");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Gateway Test Console</CardTitle>
          {ollamaStatus && (
            <Badge variant={ollamaStatus.reachable ? "success" : "destructive"}>
              Ollama {ollamaStatus.reachable ? "connected" : "offline"}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {ollamaStatus && !ollamaStatus.reachable && (
          <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
            <p className="font-medium">Ollama is not reachable</p>
            <p className="mt-1">
              Start Ollama on your machine (`ollama serve`) and pull a model (`ollama pull llama3.2`).
              Docker backend connects via {ollamaStatus.base_url}.
            </p>
          </div>
        )}

        {ollamaStatus?.models && ollamaStatus.models.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {ollamaStatus.models.map((m) => (
              <Button key={m} variant={model === m ? "default" : "outline"} size="sm" onClick={() => setModel(m)}>
                {m}
              </Button>
            ))}
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-[1fr_180px]">
          <div className="space-y-2">
            <label className="text-sm font-medium">Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-ring focus-visible:ring-2"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Model</label>
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
              placeholder="auto"
            />
            <p className="text-xs text-muted-foreground">Use <code className="text-[11px]">auto</code> to evaluate LLM Router rules.</p>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Client API key (optional)</label>
          <input
            value={clientApiKey}
            onChange={(e) => setClientApiKey(e.target.value)}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 font-mono text-xs outline-none ring-ring focus-visible:ring-2"
            placeholder="hg_… (overrides JWT; uses key's policy bundle)"
          />
          <p className="text-xs text-muted-foreground">
            Demo: <code className="text-[11px]">hg_demo_acme_support2026</code> (Standard Support) or{" "}
            <code className="text-[11px]">hg_demo_acme_copilot2026</code> (Strict Security).
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Routing context (JSON)</label>
          <textarea
            value={routingContextJson}
            onChange={(e) => setRoutingContextJson(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs outline-none ring-ring focus-visible:ring-2"
            placeholder='{"task":{"type":"code_review"},"sla":{"latency_ms":400}}'
          />
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={debugMode}
            onChange={(e) => setDebugMode(e.target.checked)}
            className="rounded border-input"
          />
          Debug response (<code className="text-xs">?mode=debug</code> — include PySetu metadata)
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={useStream}
            onChange={(e) => setUseStream(e.target.checked)}
            className="rounded border-input"
          />
          Stream response (SSE via <code className="text-xs">stream: true</code>)
        </label>

        <div className="flex flex-wrap gap-2">
          {testPrompts.map((item) => (
            <Button
              key={item.label}
              variant="outline"
              size="sm"
              onClick={() => setPrompt(item.content)}
              title={item.description}
            >
              {item.label}
              <Badge variant="outline" className="ml-1 text-[10px] capitalize">
                {item.expected}
              </Badge>
            </Button>
          ))}
        </div>

        <Button onClick={runTest} disabled={loading || (!token && !clientApiKey.trim())} className="gap-2">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          Send via /v1/chat/completions
        </Button>

        {blocked && (
          <div className="flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-red-700 dark:text-red-300" />
            <div>
              <p className="font-medium">Blocked / Error</p>
              <p className="text-red-800 dark:text-red-200">{blocked}</p>
            </div>
          </div>
        )}

        {response && (
          <div className="space-y-2 rounded-lg border border-border/60 bg-muted/20 p-3 text-sm">
            <p className="font-medium text-emerald-400">Response</p>
            <p className="whitespace-pre-wrap">{response}</p>
            {meta && (
              <div className="flex flex-wrap gap-2 pt-2">
                {meta.ollama_model && <Badge variant="success">Ollama: {meta.ollama_model}</Badge>}
                {meta.routed_model && <Badge variant="secondary">Routed: {meta.routed_model}</Badge>}
                {meta.matched_routing_rule && (
                  <Badge variant="secondary">Rule: {meta.matched_routing_rule}</Badge>
                )}
                {meta.routing_strategy && <Badge variant="outline">Strategy: {meta.routing_strategy}</Badge>}
                {meta.policy_bundle && <Badge variant="secondary">Bundle: {meta.policy_bundle}</Badge>}
                {meta.client_api_key && <Badge variant="outline">Key: {meta.client_api_key}</Badge>}
                {meta.inspection_action && <Badge variant="outline">Action: {meta.inspection_action}</Badge>}
                {meta.upstream && <Badge variant="outline">Upstream: {meta.upstream}</Badge>}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
