"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRightLeft,
  CheckCircle2,
  Cloud,
  Copy,
  Check,
  Route,
  Radar,
  Settings2,
  Shield,
} from "lucide-react";
import { GatewayTester } from "@/components/ai-gateway/gateway-tester";
import { RagGatewayTester } from "@/components/ai-gateway/rag-gateway-tester";
import { CompatibilityCenterView } from "@/components/compatibility-center/compatibility-center-view";
import { MetricCard } from "@/components/dashboard/metric-card";
import { QuickLinkPills, SectionTabBar } from "@/components/shared/section-chrome";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { API_BASE, api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const QUICK_LINKS = [
  { href: "/monitoring", label: "Monitoring", icon: Radar },
  { href: "/llm-router?tab=gateway", label: "Gateway & aliases", icon: ArrowRightLeft },
  { href: "/llm-router", label: "LLM Router", icon: Route },
] as const;

const TABS = [
  { id: "connect", label: "Connect" },
  { id: "test", label: "Test console" },
  { id: "rag", label: "Governed RAG" },
  { id: "compatibility", label: "Compatibility" },
] as const;

type GatewayTab = (typeof TABS)[number]["id"];
const TAB_IDS = new Set<string>(TABS.map((t) => t.id));

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
      "content": "Hello from PySetu"
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

const PIPELINE_STEPS = [
  "PII & secret detection on ingress",
  "Policy engine evaluation",
  "LLM router selection",
  "Output leakage scan on egress",
  "Full audit trace logging",
];

function upstreamLabel(status: {
  openai_compatible: boolean;
  gemini_compatible: boolean;
  proxy_mode?: string;
}): string {
  const parts: string[] = [];
  if (status.openai_compatible) parts.push("OpenAI");
  if (status.gemini_compatible) parts.push("Gemini");
  if (status.proxy_mode === "ollama") parts.push("Ollama");
  else if (status.proxy_mode && status.proxy_mode !== "none") parts.push(status.proxy_mode);
  return parts.length > 0 ? parts.join(" · ") : "Not configured";
}

export function AiGatewayView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = useAuthStore((s) => s.token);
  const [copiedEndpoint, setCopiedEndpoint] = useState<string | null>(null);

  const requestedTab = searchParams.get("tab");
  const initialTab: GatewayTab =
    requestedTab && TAB_IDS.has(requestedTab) ? (requestedTab as GatewayTab) : "connect";
  const [tab, setTab] = useState<GatewayTab>(initialTab);

  const { data, isLoading } = useQuery({
    queryKey: ["gateway-status", token],
    queryFn: () => api.getGatewayStatus(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const status = data ?? EMPTY_GATEWAY_STATUS;

  useEffect(() => {
    const next = searchParams.get("tab");
    if (next && TAB_IDS.has(next)) setTab(next as GatewayTab);
  }, [searchParams]);

  function selectTab(next: GatewayTab) {
    setTab(next);
    router.replace(`/ai-gateway?tab=${next}`, { scroll: false });
  }

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
    <div className="space-y-8">
      <QuickLinkPills links={QUICK_LINKS} />

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          variant="hero"
          showTrend={false}
          title="Gateway status"
          value={isLoading ? "…" : status.status.charAt(0).toUpperCase() + status.status.slice(1)}
          change={0}
          icon={Shield}
          iconColor="text-emerald-400"
          format="raw"
        />
        <MetricCard
          variant="hero"
          showTrend={false}
          title="Active upstream"
          value={upstreamLabel(status)}
          change={0}
          icon={Cloud}
          iconColor="text-blue-400"
          format="raw"
        />
        <MetricCard
          variant="hero"
          showTrend={false}
          title="Ingress endpoints"
          value={status.endpoints.length}
          change={0}
          icon={ArrowRightLeft}
          iconColor="text-violet-400"
        />
        <MetricCard
          variant="hero"
          showTrend={false}
          title="Proxy mode"
          value={!status.proxy_mode || status.proxy_mode === "none" ? "Direct" : status.proxy_mode}
          change={0}
          icon={Route}
          iconColor="text-amber-400"
          format="raw"
        />
      </section>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionTabBar tabs={TABS} active={tab} onChange={selectTab} />
        <Button variant="outline" size="sm" className="gap-1.5" asChild>
          <Link href="/settings/ai-assist#tenant-llm-defaults">
            <Settings2 className="h-3.5 w-3.5" />
            Provider defaults
          </Link>
        </Button>
      </div>

      {tab === "connect" && (
        <div className="grid gap-4 lg:grid-cols-12">
          <Card className="border-border/60 bg-card/50 lg:col-span-7">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Supported endpoints</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 font-mono text-sm">
                {status.endpoints.map((endpoint) => (
                  <li
                    key={endpoint}
                    className="flex items-center justify-between gap-2 rounded-md border border-border/60 bg-muted/20 px-3 py-2"
                  >
                    <span>
                      {gatewayHttpMethod(endpoint)} {endpoint}
                    </span>
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
              <div className="mt-3 flex flex-wrap gap-2">
                {status.openai_compatible && <Badge variant="success">OpenAI-compatible</Badge>}
                {status.gemini_compatible && <Badge variant="secondary">Gemini-compatible</Badge>}
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card/50 lg:col-span-5">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Inspection pipeline</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {PIPELINE_STEPS.map((step) => (
                <div key={step} className="flex items-center gap-2 text-sm text-muted-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
                  {step}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {tab === "test" && <GatewayTester />}

      {tab === "rag" && <RagGatewayTester />}

      {tab === "compatibility" && <CompatibilityCenterView embedded />}
    </div>
  );
}
