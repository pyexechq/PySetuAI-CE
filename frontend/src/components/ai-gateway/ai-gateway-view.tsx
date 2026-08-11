"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRightLeft, Shield, CheckCircle2, Copy, Check, Settings2, Radar } from "lucide-react";
import { GatewayTester } from "@/components/ai-gateway/gateway-tester";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { API_BASE, api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

function gatewayHttpMethod(endpoint: string): "GET" | "POST" {
  return endpoint === "/v1/models" ? "GET" : "POST";
}

function buildSampleCurl(endpoint: string): string {
  const url = `${API_BASE}${endpoint}`;
  const authHeader = "--header 'Authorization: Bearer YOUR_TOKEN_HERE'";
  const methodFlag = gatewayHttpMethod(endpoint) === "POST" ? "--request POST \\\n" : "";

  if (endpoint === "/v1/chat/completions") {
    return `curl --location '${url}' \\
${methodFlag}${authHeader} \\
--header 'Content-Type: application/json' \\
--data '{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "Hello from HelixGuard"
    }
  ]
}'`;
  }

  return `curl --location '${url}' \\
${authHeader}`;
}

const EMPTY_GATEWAY_STATUS = {
  status: "unknown",
  openai_compatible: false,
  gemini_compatible: false,
  requests_today: 0,
  blocked_today: 0,
  endpoints: ["/v1/chat/completions", "/v1/models"],
  proxy_mode: "none",
};

export function AiGatewayView() {
  const token = useAuthStore((s) => s.token);
  const [copiedEndpoint, setCopiedEndpoint] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["gateway-status", token],
    queryFn: () => api.getGatewayStatus(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const status = data ?? EMPTY_GATEWAY_STATUS;

  async function copySampleCurl(endpoint: string) {
    try {
      await navigator.clipboard.writeText(buildSampleCurl(endpoint));
      setCopiedEndpoint(endpoint);
      window.setTimeout(() => setCopiedEndpoint(null), 2000);
    } catch {
      // clipboard unavailable
    }
  }

  return (
    <div className="space-y-6">
      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading gateway status…</p>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 bg-card/50">
          <CardContent className="flex items-center gap-3 p-5">
            <div className="rounded-lg bg-emerald-500/10 p-2">
              <Shield className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Gateway status</p>
              <p className="font-semibold capitalize">{status.status}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm text-muted-foreground">Active upstream</p>
                <div className="mt-1 flex flex-wrap gap-2">
                  {status.openai_compatible && <Badge variant="success">OpenAI</Badge>}
                  {status.gemini_compatible && <Badge variant="secondary">Gemini</Badge>}
                  <Badge variant="outline">
                    {status.proxy_mode === "ollama"
                      ? "Ollama"
                      : status.proxy_mode === "openai"
                        ? "OpenAI"
                        : status.proxy_mode === "gemini"
                          ? "Gemini"
                          : status.proxy_mode === "none"
                            ? "Not configured"
                            : status.proxy_mode}
                  </Badge>
                </div>
              </div>
              <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs" asChild>
                <Link href="/settings/integrations">
                  <Settings2 className="h-3.5 w-3.5" />
                  Configure
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/50">
          <CardContent className="space-y-3 p-5">
            <p className="text-sm text-muted-foreground">Request volume & blocks</p>
            <p className="text-xs text-muted-foreground">
              Live traffic KPIs and trends are in Monitoring — this page focuses on ingress endpoints and testing.
            </p>
            <Button variant="outline" size="sm" className="gap-1.5" asChild>
              <Link href="/monitoring">
                <Radar className="h-3.5 w-3.5" />
                Open Monitoring
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap gap-2 rounded-lg border border-border/60 bg-muted/20 px-4 py-3">
        <span className="text-xs text-muted-foreground">Related:</span>
        <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs" asChild>
          <Link href="/settings/uag">
            <ArrowRightLeft className="h-3.5 w-3.5" />
            UAG mappings & policies
          </Link>
        </Button>
        <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs" asChild>
          <Link href="/compatibility-center">Compatibility Center</Link>
        </Button>
        <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs" asChild>
          <Link href="/llm-router">LLM Router</Link>
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" />
              Supported Endpoints
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 font-mono text-sm">
              {status.endpoints.map((endpoint) => (
                <li
                  key={endpoint}
                  className="flex items-center justify-between gap-2 rounded-md border border-border/60 bg-muted/20 px-3 py-2"
                >
                  <span>{gatewayHttpMethod(endpoint)} {endpoint}</span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 shrink-0 gap-1.5 font-sans text-xs text-muted-foreground"
                    onClick={() => copySampleCurl(endpoint)}
                    aria-label={`Copy sample cURL for ${endpoint}`}
                  >
                    {copiedEndpoint === endpoint ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        Copy cURL
                      </>
                    )}
                  </Button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle>Inspection Pipeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              "PII & secret detection on ingress",
              "Policy engine evaluation",
              "LLM router selection",
              "Output leakage scan on egress",
              "Full audit trace logging",
              "OpenAI-compatible /v1/chat/completions",
            ].map((step) => (
              <div key={step} className="flex items-center gap-2 text-sm">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                {step}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <GatewayTester />
    </div>
  );
}
