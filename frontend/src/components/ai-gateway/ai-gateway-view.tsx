"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowRightLeft,
  CheckCircle2,
  Cloud,
  Code2,
  Copy,
  Check,
  Cpu,
  ExternalLink,
  Flame,
  Globe,
  KeyRound,
  Layers,
  Lock,
  Play,
  Radar,
  RefreshCw,
  Route,
  Server,
  Settings2,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  Zap,
} from "lucide-react";
import { GatewayTester } from "@/components/ai-gateway/gateway-tester";
import { RagGatewayTester } from "@/components/ai-gateway/rag-gateway-tester";
import { CompatibilityCenterView } from "@/components/compatibility-center/compatibility-center-view";
import { TenantEdgeMeshPanel } from "@/components/settings/tenant-edge-mesh-panel";
import { QuickLinkPills, SectionTabBar } from "@/components/shared/section-chrome";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const QUICK_LINKS = [
  { href: "/monitoring", label: "Monitoring & Traces", icon: Radar },
  { href: "/llm-router?tab=gateway", label: "Gateway & Aliases", icon: ArrowRightLeft },
  { href: "/llm-router", label: "LLM Router", icon: Route },
  { href: "/settings/edge-gateways", label: "Edge Mesh Settings", icon: Server },
] as const;

const TABS = [
  { id: "connect", label: "Connect & Ingress Hub" },
  { id: "test", label: "Interactive Test Console" },
  { id: "edge-mesh", label: "Edge Mesh Nodes" },
  { id: "rag", label: "Governed RAG" },
  { id: "compatibility", label: "Protocol Compatibility" },
] as const;

type GatewayTab = (typeof TABS)[number]["id"];
const TAB_IDS = new Set<string>(TABS.map((t) => t.id));

function gatewayHttpMethod(endpoint: string): "GET" | "POST" {
  return endpoint === "/v1/models" || endpoint === "/models" ? "GET" : "POST";
}

function buildSampleCurl(endpoint: string, origin: string = "https://pysetu.io"): string {
  const cleanEndpoint = endpoint.startsWith("/api/v1") ? endpoint.replace("/api/v1", "/v1") : endpoint;
  const url = `${origin}${cleanEndpoint}`;
  const authHeader = "--header 'Authorization: Bearer YOUR_TOKEN_HERE'";
  const methodFlag = gatewayHttpMethod(cleanEndpoint) === "POST" ? "--request POST \\\n" : "";

  if (cleanEndpoint.includes(":generateContent") || cleanEndpoint.startsWith("/v1beta")) {
    return `curl --location '${origin}/v1beta/models/gemini-1.5-pro:generateContent' \\
--request POST \\
${authHeader} \\
--header 'Content-Type: application/json' \\
--data '{
  "contents": [
    {
      "parts": [
        {
          "text": "Hello from PySetu Gemini Gateway"
        }
      ]
    }
  ]
}'`;
  }

  if (cleanEndpoint === "/v1/messages" || cleanEndpoint.includes("/messages")) {
    return `curl --location '${origin}/v1/messages' \\
--request POST \\
--header 'x-api-key: YOUR_TOKEN_HERE' \\
--header 'anthropic-version: 2023-06-01' \\
--header 'Content-Type: application/json' \\
--data '{
  "model": "claude-3-7-sonnet-20250219",
  "max_tokens": 1024,
  "messages": [
    {
      "role": "user",
      "content": "Hello from PySetu Anthropic Gateway"
    }
  ]
}'`;
  }

  if (cleanEndpoint === "/v1/chat/completions") {
    return `curl --location '${origin}/v1/chat/completions' \\
${methodFlag}${authHeader} \\
--header 'Content-Type: application/json' \\
--data '{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": "Hello from PySetu AI Gateway"
    }
  ]
}'`;
  }

  return `curl --location '${url}' \\
${authHeader}`;
}

const EMPTY_GATEWAY_STATUS = {
  status: "operational",
  openai_compatible: true,
  gemini_compatible: true,
  anthropic_compatible: true,
  requests_today: 0,
  blocked_today: 0,
  endpoints: [
    "/v1/chat/completions",
    "/v1/messages",
    "/v1/models",
    "/v1/mcp",
    "/v1beta/models/{model}:generateContent",
  ],
  proxy_mode: "mock",
  opa_available: true,
  opa_enabled: true,
};

const PIPELINE_STEPS = [
  {
    step: "01",
    title: "Zero-AI Ingress Guard",
    latency: "<0.3ms",
    desc: "Deterministic AST & Regex scan for prompt injection, jailbreaks, and system override attempts before invoking LLMs.",
    badge: "267μs",
    badgeColor: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    icon: ShieldCheck,
  },
  {
    step: "02",
    title: "Presidio / Regex PII Masking",
    latency: "<1.2ms",
    desc: "Bidirectional redaction and tokenization of SSNs, emails, API keys, passwords, and custom enterprise DLP entities.",
    badge: "Real-time Masking",
    badgeColor: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
    icon: Lock,
  },
  {
    step: "03",
    title: "OPA Universal Policy Engine",
    latency: "<0.8ms",
    desc: "Rego-based policy enforcement for tenant rate limits, role-based tool permissions, and model authorization.",
    badge: "Active OPA",
    badgeColor: "bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20",
    icon: Cpu,
  },
  {
    step: "04",
    title: "Dynamic Cost Arbitrage Router",
    latency: "<0.5ms",
    desc: "Analyzes prompt complexity and routes routine queries to cost-efficient models (e.g. GPT-4o-mini), saving up to 94%.",
    badge: "94% Cost Saving",
    badgeColor: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20",
    icon: Route,
  },
  {
    step: "05",
    title: "Multi-Upstream Execution",
    latency: "Native",
    desc: "Streams inference directly from OpenAI, Google Gemini, Anthropic Claude, or local Ollama with zero-hop connection pooling.",
    badge: "Zero-Hop Pool",
    badgeColor: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
    icon: Cloud,
  },
  {
    step: "06",
    title: "Egress DLP & Audit Trail",
    latency: "<1.0ms",
    desc: "Scans generated tokens for confidential data leaks, records tamper-proof cryptographic audit hashes, and logs telemetry.",
    badge: "SHA-256 Trail",
    badgeColor: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    icon: Sparkles,
  },
];

export function AiGatewayView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = useAuthStore((s) => s.token);
  const [copiedEndpoint, setCopiedEndpoint] = useState<string | null>(null);
  const [activeSnippetTab, setActiveSnippetTab] = useState<
    "python-openai" | "python-anthropic" | "python-gemini" | "typescript" | "curl" | "ide"
  >("python-openai");
  const [origin, setOrigin] = useState<string>("https://pysetu.io");

  useEffect(() => {
    if (typeof window !== "undefined" && window.location.origin) {
      setOrigin(window.location.origin);
    }
  }, []);

  const requestedTab = searchParams.get("tab");
  const initialTab: GatewayTab =
    requestedTab && TAB_IDS.has(requestedTab) ? (requestedTab as GatewayTab) : "connect";
  const [tab, setTab] = useState<GatewayTab>(initialTab);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["gateway-status", token],
    queryFn: () => api.getGatewayStatus(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const status = data ?? EMPTY_GATEWAY_STATUS;

  // Clean endpoints list
  const cleanEndpoints = Array.from(
    new Set(
      status.endpoints
        .map((e) => (e.startsWith("/api/v1") ? e.replace("/api/v1", "/v1") : e))
        .filter((e) => !e.startsWith("/api/v1/"))
    )
  );

  useEffect(() => {
    const next = searchParams.get("tab");
    if (next && TAB_IDS.has(next)) setTab(next as GatewayTab);
  }, [searchParams]);

  function selectTab(next: GatewayTab) {
    setTab(next);
    router.replace(`/ai-gateway?tab=${next}`, { scroll: false });
  }

  async function copyText(text: string, id: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedEndpoint(id);
      window.setTimeout(() => setCopiedEndpoint(null), 2000);
    } catch {
      // clipboard fallback
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Quicklinks Ribbon */}
      <QuickLinkPills links={QUICK_LINKS} />

      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-4 sm:p-6 shadow-sm">
        {/* Subtle Background Glow */}
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between w-full min-w-0">
          {/* Status & Highlights */}
          <div className="space-y-2.5 w-full min-w-0 max-w-xl">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Gateway Operational
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                &lt;0.3ms Zero-AI Ingress Guard
              </Badge>
              <Badge variant="outline" className="bg-muted text-muted-foreground border-border/60 text-xs font-mono">
                Universal Protocol Mesh
              </Badge>
            </div>

            <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-foreground break-words">
              Enterprise AI Gateway & Ingress Mesh
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Unified, high-speed reverse proxy with native protocol translation across OpenAI, Google Gemini, Anthropic Claude, and Regional Edge Wasm Mesh.
            </p>

            {/* Protocol Support Pills */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                Protocols:
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] sm:text-xs font-semibold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="h-3 w-3" /> OpenAI v1
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] sm:text-xs font-semibold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="h-3 w-3" /> Gemini v1beta
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] sm:text-xs font-semibold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="h-3 w-3" /> Anthropic Claude v1
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] sm:text-xs font-semibold px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                <Zap className="h-3 w-3" /> Edge Mesh
              </span>
            </div>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-2.5 sm:gap-3 w-full lg:w-auto shrink-0">
            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Ingress Health</span>
                <Shield className="h-3.5 w-3.5 text-emerald-500" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-foreground">100%</p>
              <p className="text-[10px] text-muted-foreground">OPA + DLP Active</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Today&apos;s Traffic</span>
                <Cloud className="h-3.5 w-3.5 text-blue-500" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-foreground">{status.requests_today || 0}</p>
              <p className="text-[10px] text-muted-foreground">Requests processed</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Threats Blocked</span>
                <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-rose-600 dark:text-rose-400">{status.blocked_today || 0}</p>
              <p className="text-[10px] text-muted-foreground">Zero-AI Guarded</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Gateway Latency</span>
                <Zap className="h-3.5 w-3.5 text-amber-500" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-emerald-600 dark:text-emerald-400">&lt; 0.3 ms</p>
              <p className="text-[10px] text-muted-foreground">Pre-flight overhead</p>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Navigation Tabs & Provider Action ───────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
        <SectionTabBar tabs={TABS} active={tab} onChange={selectTab} />
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading} className="gap-1.5 text-xs h-8">
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button variant="outline" size="sm" className="gap-1.5 text-xs h-8" asChild>
            <Link href="/settings/ai-assist#tenant-llm-defaults">
              <Settings2 className="h-3.5 w-3.5 text-primary" />
              Provider Defaults
            </Link>
          </Button>
        </div>
      </div>

      {/* ─── TAB 1: Connect & Ingress Hub ────────────────────────────────────── */}
      {tab === "connect" && (
        <div className="space-y-8">
          {/* Multi-Protocol Ingress Hub Grid */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                  <Globe className="h-4 w-4 text-primary" />
                  Protocol Ingress Gateways & Base URLs
                </h2>
                <p className="text-xs text-muted-foreground">
                  Point any official LLM SDK or AI agent framework directly to PySetu Gateway endpoints.
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => selectTab("test")}
                className="text-xs text-primary hover:text-primary gap-1 h-7 font-medium"
              >
                <Play className="h-3.5 w-3.5" />
                Open Live Test Console
              </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {/* Card 1: OpenAI v1 */}
              <Card className="border-border/80 bg-card/70 shadow-xs hover:border-primary/40 transition-all flex flex-col justify-between">
                <CardHeader className="pb-2 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-emerald-500" />
                      OpenAI & Standard
                    </span>
                    <Badge variant="outline" className="text-[9px] font-mono text-emerald-600 dark:text-emerald-400 border-emerald-500/30">
                      OPENAI v1
                    </Badge>
                  </div>
                  <CardDescription className="text-[11px]">
                    Universal OpenAI SDK & REST chat completions.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 pt-2">
                  <div className="rounded-lg bg-muted/40 p-2.5 border border-border/60">
                    <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider">Base URL</p>
                    <code className="text-xs font-mono font-bold text-foreground block truncate mt-0.5">
                      {origin}/v1
                    </code>
                  </div>
                  <div className="space-y-1 text-[11px] font-mono text-muted-foreground">
                    <p className="text-foreground font-semibold text-[10px] uppercase font-sans">Endpoints</p>
                    <p className="truncate">POST /v1/chat/completions</p>
                    <p className="truncate">GET /v1/models</p>
                    <p className="truncate">POST /v1/mcp</p>
                  </div>
                  <div className="pt-2 flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full text-xs h-7 gap-1"
                      onClick={() => copyText(`${origin}/v1`, "openai-url")}
                    >
                      {copiedEndpoint === "openai-url" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          Copy Base URL
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Card 2: Google Gemini v1beta */}
              <Card className="border-border/80 bg-card/70 shadow-xs hover:border-cyan-500/40 transition-all flex flex-col justify-between">
                <CardHeader className="pb-2 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-cyan-500" />
                      Google Gemini
                    </span>
                    <Badge variant="outline" className="text-[9px] font-mono text-cyan-600 dark:text-cyan-400 border-cyan-500/30">
                      GEMINI v1BETA
                    </Badge>
                  </div>
                  <CardDescription className="text-[11px]">
                    Native Google GenAI SDK & Vertex integration.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 pt-2">
                  <div className="rounded-lg bg-muted/40 p-2.5 border border-border/60">
                    <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider">Base URL</p>
                    <code className="text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400 block truncate mt-0.5">
                      {origin}/v1beta
                    </code>
                  </div>
                  <div className="space-y-1 text-[11px] font-mono text-muted-foreground">
                    <p className="text-foreground font-semibold text-[10px] uppercase font-sans">Endpoints</p>
                    <p className="truncate">POST /v1beta/models/...:generateContent</p>
                    <p className="truncate">POST /v1beta/models/...:streamGenerateContent</p>
                  </div>
                  <div className="pt-2 flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full text-xs h-7 gap-1"
                      onClick={() => copyText(`${origin}/v1beta`, "gemini-url")}
                    >
                      {copiedEndpoint === "gemini-url" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          Copy Gemini URL
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Card 3: Anthropic Claude v1 */}
              <Card className="border-border/80 bg-card/70 shadow-xs hover:border-amber-500/40 transition-all flex flex-col justify-between">
                <CardHeader className="pb-2 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-amber-500" />
                      Anthropic Claude
                    </span>
                    <Badge variant="outline" className="text-[9px] font-mono text-amber-600 dark:text-amber-400 border-amber-500/30">
                      ANTHROPIC v1
                    </Badge>
                  </div>
                  <CardDescription className="text-[11px]">
                    Native Anthropic Messages API & Claude Code.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 pt-2">
                  <div className="rounded-lg bg-muted/40 p-2.5 border border-border/60">
                    <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider">Base URL</p>
                    <code className="text-xs font-mono font-bold text-amber-600 dark:text-amber-400 block truncate mt-0.5">
                      {origin}/v1
                    </code>
                  </div>
                  <div className="space-y-1 text-[11px] font-mono text-muted-foreground">
                    <p className="text-foreground font-semibold text-[10px] uppercase font-sans">Endpoints</p>
                    <p className="truncate">POST /v1/messages</p>
                    <p className="truncate">POST /v1/messages?stream=true</p>
                  </div>
                  <div className="pt-2 flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full text-xs h-7 gap-1"
                      onClick={() => copyText(`${origin}/v1`, "anthropic-url")}
                    >
                      {copiedEndpoint === "anthropic-url" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          Copy Anthropic URL
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Card 4: Regional Edge Mesh */}
              <Card className="border-border/80 bg-card/70 shadow-xs hover:border-primary/40 transition-all flex flex-col justify-between bg-gradient-to-br from-primary/5 via-card to-card">
                <CardHeader className="pb-2 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <Zap className="h-3.5 w-3.5 text-emerald-500" />
                      Regional Edge Mesh
                    </span>
                    <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-[9px] font-semibold">
                      SUB-2MS
                    </Badge>
                  </div>
                  <CardDescription className="text-[11px]">
                    Stateless Wasm edge mesh nodes in client VPCs.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 pt-2">
                  <div className="rounded-lg bg-primary/10 p-2.5 border border-primary/20">
                    <p className="text-[10px] text-primary font-mono uppercase tracking-wider">Mesh Endpoint</p>
                    <code className="text-xs font-mono font-bold text-foreground block truncate mt-0.5">
                      https://[region].edge.pysetu.io/v1
                    </code>
                  </div>
                  <div className="space-y-1 text-[11px] font-mono text-muted-foreground">
                    <p className="text-foreground font-semibold text-[10px] uppercase font-sans">Features</p>
                    <p className="truncate">Local Wasm OPA + Presidio DLP</p>
                    <p className="truncate">Zero Cloud Ingress Roundtrip</p>
                  </div>
                  <div className="pt-2 flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      className="w-full text-xs h-7 gap-1 font-medium"
                      onClick={() => selectTab("edge-mesh")}
                    >
                      <Server className="h-3.5 w-3.5 text-primary" />
                      Manage Edge Nodes
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* ─── Two-Column: Supported Endpoints & Interactive SDK Studio ───── */}
          <div className="grid gap-6 lg:grid-cols-12">
            {/* Left: Supported API Endpoints */}
            <Card className="border-border/80 bg-card/60 lg:col-span-5 shadow-xs flex flex-col justify-between">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-primary" />
                  Supported Gateway Endpoints
                </CardTitle>
                <CardDescription className="text-xs">
                  Copy sample cURL commands for any supported gateway protocol.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 flex-1 flex flex-col justify-between">
                <ul className="space-y-2 font-mono text-xs">
                  {cleanEndpoints.map((endpoint) => (
                    <li
                      key={endpoint}
                      className="flex items-center justify-between gap-2 rounded-xl border border-border/60 bg-muted/20 px-3 py-2 hover:bg-muted/40 transition-colors"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary uppercase">
                          {gatewayHttpMethod(endpoint)}
                        </span>
                        <span className="text-xs font-medium text-foreground truncate">{endpoint}</span>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-6 shrink-0 gap-1 font-sans text-[11px] text-muted-foreground hover:text-foreground"
                        onClick={() => copyText(buildSampleCurl(endpoint, origin), endpoint)}
                        aria-label={`Copy sample cURL for ${endpoint}`}
                      >
                        {copiedEndpoint === endpoint ? (
                          <>
                            <Check className="h-3 w-3 text-emerald-400" />
                            <span className="text-emerald-500 font-medium">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3" />
                            <span>cURL</span>
                          </>
                        )}
                      </Button>
                    </li>
                  ))}
                </ul>

                <div className="pt-3 border-t border-border/60 flex items-center justify-between text-xs text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <KeyRound className="h-3.5 w-3.5 text-primary" />
                    Auth via Bearer Token or <code className="text-foreground font-mono">x-api-key</code>
                  </span>
                  <Link href="/developer-portal/api-keys" className="text-primary hover:underline text-xs font-medium">
                    Manage Keys →
                  </Link>
                </div>
              </CardContent>
            </Card>

            {/* Right: Multi-Language SDK Code Studio */}
            <Card className="border-border/80 bg-card/60 lg:col-span-7 shadow-xs flex flex-col justify-between">
              <CardHeader className="pb-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <Code2 className="h-4 w-4 text-primary" />
                    Multi-Language SDK & Agent Studio
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Drop-in client configurations for Python, Node.js, and IDEs.
                  </CardDescription>
                </div>

                {/* Tab Switcher */}
                <div className="flex flex-wrap items-center gap-1 bg-muted/40 p-1 rounded-xl border border-border/60">
                  <button
                    onClick={() => setActiveSnippetTab("python-openai")}
                    className={`px-2 py-0.5 text-xs rounded-lg font-medium transition-all ${
                      activeSnippetTab === "python-openai"
                        ? "bg-card text-foreground font-bold shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    OpenAI
                  </button>
                  <button
                    onClick={() => setActiveSnippetTab("python-anthropic")}
                    className={`px-2 py-0.5 text-xs rounded-lg font-medium transition-all ${
                      activeSnippetTab === "python-anthropic"
                        ? "bg-card text-foreground font-bold shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Anthropic
                  </button>
                  <button
                    onClick={() => setActiveSnippetTab("python-gemini")}
                    className={`px-2 py-0.5 text-xs rounded-lg font-medium transition-all ${
                      activeSnippetTab === "python-gemini"
                        ? "bg-card text-foreground font-bold shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Gemini
                  </button>
                  <button
                    onClick={() => setActiveSnippetTab("typescript")}
                    className={`px-2 py-0.5 text-xs rounded-lg font-medium transition-all ${
                      activeSnippetTab === "typescript"
                        ? "bg-card text-foreground font-bold shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    TypeScript
                  </button>
                  <button
                    onClick={() => setActiveSnippetTab("ide")}
                    className={`px-2 py-0.5 text-xs rounded-lg font-medium transition-all ${
                      activeSnippetTab === "ide"
                        ? "bg-card text-foreground font-bold shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    IDE / Cursor
                  </button>
                </div>
              </CardHeader>

              <CardContent className="space-y-3 pt-2">
                <div className="relative">
                  <pre className="p-4 rounded-xl bg-slate-950 text-slate-100 font-mono text-xs overflow-x-auto leading-relaxed border border-slate-800 max-h-64 shadow-inner">
                    {activeSnippetTab === "python-openai" &&
`# Python: OpenAI SDK via PySetu AI Gateway
from openai import OpenAI

client = OpenAI(
    base_url="${origin}/v1",
    api_key="pysetu_live_secret_..."
)

response = client.chat.completions.create(
    model="gpt-4o",  # auto-translated by PySetu router
    messages=[{"role": "user", "content": "Process financial records"}]
)
print(response.choices[0].message.content)`}

                    {activeSnippetTab === "python-anthropic" &&
`# Python: Anthropic SDK via PySetu AI Gateway
from anthropic import Anthropic

client = Anthropic(
    base_url="${origin}",
    api_key="pysetu_live_secret_..."
)

response = client.messages.create(
    model="claude-3-7-sonnet",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Execute agentic tool sequence"}]
)
print(response.content[0].text)`}

                    {activeSnippetTab === "python-gemini" &&
`# Python: Google GenAI SDK via PySetu AI Gateway
import google.generativeai as genai

genai.configure(
    api_key="pysetu_live_secret_...",
    client_options={"api_endpoint": "${origin}"}
)

model = genai.GenerativeModel("gemini-1.5-pro")
response = model.generate_content("Analyze multimodal data with PySetu DLP")
print(response.text)`}

                    {activeSnippetTab === "typescript" &&
`// TypeScript / Node.js: OpenAI SDK
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "${origin}/v1",
  apiKey: process.env.PYSETU_API_KEY || "pysetu_live_secret_...",
});

const completion = await client.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "Safe agentic inference" }],
});
console.log(completion.choices[0].message.content);`}

                    {activeSnippetTab === "ide" &&
`// Cursor IDE / VS Code / Claude Code Settings
// Settings JSON (~/.cursor/settings.json or VSCode settings):
{
  "openai.baseURL": "${origin}/v1",
  "openai.apiKey": "pysetu_live_secret_...",
  "anthropic.baseURL": "${origin}/v1",
  "anthropic.apiKey": "pysetu_live_secret_..."
}`}
                  </pre>

                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      const snippet =
                        activeSnippetTab === "python-openai"
                          ? `from openai import OpenAI\n\nclient = OpenAI(base_url="${origin}/v1", api_key="pysetu_live_secret_...")\nresponse = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": "Process financial records"}])\nprint(response.choices[0].message.content)`
                          : activeSnippetTab === "python-anthropic"
                          ? `from anthropic import Anthropic\n\nclient = Anthropic(base_url="${origin}", api_key="pysetu_live_secret_...")\nresponse = client.messages.create(model="claude-3-7-sonnet", max_tokens=1024, messages=[{"role": "user", "content": "Execute agentic tool sequence"}])\nprint(response.content[0].text)`
                          : activeSnippetTab === "python-gemini"
                          ? `import google.generativeai as genai\n\ngenai.configure(api_key="pysetu_live_secret_...", client_options={"api_endpoint": "${origin}"})\nmodel = genai.GenerativeModel("gemini-1.5-pro")\nresponse = model.generate_content("Analyze multimodal data with PySetu DLP")\nprint(response.text)`
                          : activeSnippetTab === "typescript"
                          ? `import OpenAI from "openai";\n\nconst client = new OpenAI({ baseURL: "${origin}/v1", apiKey: "pysetu_live_secret_..." });\nconst completion = await client.chat.completions.create({ model: "gpt-4o", messages: [{ role: "user", content: "Safe agentic inference" }] });\nconsole.log(completion.choices[0].message.content);`
                          : `OpenAI Base URL: ${origin}/v1\nAnthropic Base URL: ${origin}/v1\nAPI Key: pysetu_live_secret_...`;
                      copyText(snippet, "active-snippet");
                    }}
                    className="absolute top-3 right-3 h-7 text-xs gap-1.5 bg-slate-800/90 hover:bg-slate-700 text-slate-200 border border-slate-700 shadow-sm"
                  >
                    {copiedEndpoint === "active-snippet" ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                        <span>Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        <span>Copy Code</span>
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* ─── End-to-End Security & Governance Pipeline Diagram ──────────── */}
          <div className="rounded-2xl border border-border/80 bg-card/60 p-6 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-border/60 pb-4">
              <div>
                <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-500" />
                  Zero-AI Pre-Flight & Reverse Proxy Pipeline
                </h2>
                <p className="text-xs text-muted-foreground">
                  Every request entering the AI Gateway undergoes 6-step deterministic inspection before touching upstream LLMs.
                </p>
              </div>
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 text-xs font-semibold self-start sm:self-center">
                Sub-2ms Total Inspection Budget
              </Badge>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
              {PIPELINE_STEPS.map((step) => {
                const Icon = step.icon;
                return (
                  <div
                    key={step.step}
                    className="relative flex flex-col justify-between rounded-xl border border-border/70 bg-card p-4 shadow-xs transition-all hover:border-primary/40 group"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-xs font-bold text-muted-foreground">
                          {step.step}
                        </span>
                        <div className="h-7 w-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center group-hover:scale-105 transition-transform">
                          <Icon className="h-3.5 w-3.5" />
                        </div>
                      </div>
                      <h3 className="text-xs font-bold text-foreground mb-1">
                        {step.title}
                      </h3>
                      <p className="text-[11px] text-muted-foreground leading-relaxed">
                        {step.desc}
                      </p>
                    </div>

                    <div className="mt-3 pt-2 border-t border-border/50 flex items-center justify-between">
                      <span className="text-[10px] font-mono text-muted-foreground">
                        {step.latency}
                      </span>
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${step.badgeColor}`}>
                        {step.badge}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB 2: Live Test Console ────────────────────────────────────────── */}
      {tab === "test" && <GatewayTester />}

      {/* ─── TAB 3: Edge Mesh Nodes ─────────────────────────────────────────── */}
      {tab === "edge-mesh" && <TenantEdgeMeshPanel />}

      {/* ─── TAB 4: Governed RAG ────────────────────────────────────────────── */}
      {tab === "rag" && <RagGatewayTester />}

      {/* ─── TAB 5: Protocol Compatibility ──────────────────────────────────── */}
      {tab === "compatibility" && <CompatibilityCenterView embedded />}
    </div>
  );
}
