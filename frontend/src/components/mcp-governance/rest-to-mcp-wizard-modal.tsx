"use client";

/**
 * BL-083 — REST-to-MCP Auto-Proxy Wizard (Flagship P1)
 *
 * 3-step wizard:
 *   Step 1 — Protocol & Schema input (OpenAPI URL / Postman JSON / GraphQL SDL)
 *   Step 2 — Tool preview (auto-parsed from spec; user can toggle tools to include)
 *   Step 3 — Server config & RBAC (name, category, RBAC groups, register)
 */

import { useState, useCallback } from "react";
import {
  ArrowLeft, ArrowRight, Check, CheckCircle2, ChevronDown, ChevronRight,
  Code2, FileJson, Loader2, Network, Plus, Shield, Wand2, X, AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

// ─── types ────────────────────────────────────────────────────────────────────

type Protocol = "openapi_url" | "openapi_json" | "postman" | "graphql";

interface ParsedTool {
  name: string;
  description: string;
  method?: string;
  path?: string;
  tags?: string[];
  selected: boolean;
}

interface WizardProps {
  open: boolean;
  token: string | null;
  categorySuggestions: string[];
  onClose: () => void;
  onSaved: () => void;
}

const DEFAULT_CATEGORIES = [
  "Human Resources", "Finance", "Sales", "Productivity", "Engineering", "Operations",
];

// ─── helpers ──────────────────────────────────────────────────────────────────

function toToolName(raw: string): string {
  return raw.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 64);
}

function parseOpenApiSpec(spec: Record<string, unknown>): ParsedTool[] {
  const paths = (spec.paths ?? {}) as Record<string, unknown>;
  const tools: ParsedTool[] = [];
  const HTTP_METHODS = ["get", "post", "put", "patch", "delete", "head"];
  for (const [path, pathItem] of Object.entries(paths)) {
    if (!pathItem || typeof pathItem !== "object") continue;
    for (const method of HTTP_METHODS) {
      const op = (pathItem as Record<string, unknown>)[method];
      if (!op || typeof op !== "object") continue;
      const opObj = op as Record<string, unknown>;
      const operationId = String(opObj.operationId ?? "");
      const summary = String(opObj.summary ?? "");
      const description = String(opObj.description ?? summary);
      const tags = Array.isArray(opObj.tags) ? (opObj.tags as string[]) : [];
      const rawName = operationId || `${method}_${path.replace(/\//g, "_").replace(/[{}]/g, "")}`;
      tools.push({
        name: toToolName(rawName),
        description: description || `${method.toUpperCase()} ${path}`,
        method: method.toUpperCase(),
        path,
        tags,
        selected: true,
      });
    }
  }
  return tools;
}

function parsePostmanSpec(collection: Record<string, unknown>): ParsedTool[] {
  const tools: ParsedTool[] = [];
  function traverse(items: unknown[]) {
    for (const item of items) {
      if (!item || typeof item !== "object") continue;
      const it = item as Record<string, unknown>;
      if (Array.isArray(it.item)) { traverse(it.item as unknown[]); continue; }
      if (it.request) {
        const req = it.request as Record<string, unknown>;
        const name = String(it.name ?? "");
        const method = String((req.method as string) ?? "GET");
        const urlObj = req.url as Record<string, unknown> | string | undefined;
        const rawPath = typeof urlObj === "string"
          ? urlObj
          : Array.isArray((urlObj as Record<string, unknown>)?.path)
            ? ((urlObj as Record<string, unknown>).path as string[]).join("/")
            : "";
        tools.push({ name: toToolName(name || rawPath), description: `${method} ${rawPath}` || name, method, path: rawPath, tags: [], selected: true });
      }
    }
  }
  if (Array.isArray(collection.item)) traverse(collection.item as unknown[]);
  return tools;
}

function parseGraphQlSdl(sdl: string): ParsedTool[] {
  const tools: ParsedTool[] = [];
  const blockRe = /\b(type\s+)(Mutation|Query)\s*\{([^}]+)\}/gi;
  let blockMatch: RegExpExecArray | null;
  while ((blockMatch = blockRe.exec(sdl)) !== null) {
    const kind = blockMatch[2].toLowerCase();
    const body = blockMatch[3];
    const fieldRe = /(\w+)\s*(?:\([^)]*\))?\s*:/g;
    let fieldMatch: RegExpExecArray | null;
    while ((fieldMatch = fieldRe.exec(body)) !== null) {
      const fieldName = fieldMatch[1];
      if (fieldName === "__typename") continue;
      tools.push({ name: toToolName(fieldName), description: `GraphQL ${kind}: ${fieldName}`, method: kind === "mutation" ? "MUTATION" : "QUERY", path: fieldName, tags: [kind], selected: true });
    }
  }
  return tools;
}

// ─── sub-components ───────────────────────────────────────────────────────────

function StepDot({ step, active, done }: { step: number; active: boolean; done: boolean }) {
  return (
    <div className={cn("flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-bold transition-all", done ? "border-emerald-500 bg-emerald-500/20 text-emerald-400" : active ? "border-primary bg-primary/10 text-primary" : "border-border/60 bg-muted/20 text-muted-foreground")}>
      {done ? <Check className="h-4 w-4" /> : step}
    </div>
  );
}

function StepConnector({ done }: { done: boolean }) {
  return <div className={cn("h-0.5 flex-1 mx-1 rounded", done ? "bg-emerald-500/50" : "bg-border/60")} />;
}

// ─── main wizard ──────────────────────────────────────────────────────────────

export function RestToMcpWizardModal({ open, token, categorySuggestions, onClose, onSaved }: WizardProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [protocol, setProtocol] = useState<Protocol>("openapi_url");
  const [specUrl, setSpecUrl] = useState("");
  const [specText, setSpecText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [tools, setTools] = useState<ParsedTool[]>([]);
  const [expandedTool, setExpandedTool] = useState<string | null>(null);
  const categories = Array.from(new Set([...DEFAULT_CATEGORIES, ...categorySuggestions])).sort();
  const [serverName, setServerName] = useState("");
  const [serverCategory, setServerCategory] = useState("Engineering");
  const [endpointUrl, setEndpointUrl] = useState("");
  const [rbacGroups, setRbacGroups] = useState<string[]>(["ai_user"]);
  const [saving, setSaving] = useState(false);
  const [savedOk, setSavedOk] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const selectedTools = tools.filter((t) => t.selected);

  const reset = useCallback(() => {
    setStep(1); setProtocol("openapi_url"); setSpecUrl(""); setSpecText(""); setParsing(false);
    setParseError(null); setTools([]); setExpandedTool(null); setServerName("");
    setServerCategory("Engineering"); setEndpointUrl(""); setRbacGroups(["ai_user"]);
    setSaving(false); setSavedOk(false); setSaveError(null);
  }, []);

  function handleClose() { reset(); onClose(); }

  async function parseSpec() {
    setParseError(null); setParsing(true);
    let parsed: ParsedTool[] = [];
    try {
      if (protocol === "openapi_url") {
        if (!specUrl.trim()) throw new Error("Please enter an OpenAPI spec URL");
        const resp = await fetch(specUrl.trim());
        if (!resp.ok) throw new Error(`Fetch failed: ${resp.status} ${resp.statusText}`);
        const spec = (await resp.json()) as Record<string, unknown>;
        parsed = parseOpenApiSpec(spec);
        setEndpointUrl(String((spec.servers as Array<{ url: string }> | undefined)?.[0]?.url ?? (spec.host ? `https://${spec.host}${spec.basePath ?? ""}` : "")));
      } else if (protocol === "openapi_json") {
        const spec = JSON.parse(specText) as Record<string, unknown>;
        parsed = parseOpenApiSpec(spec);
        setEndpointUrl(String((spec.servers as Array<{ url: string }> | undefined)?.[0]?.url ?? ""));
      } else if (protocol === "postman") {
        const col = JSON.parse(specText) as Record<string, unknown>;
        parsed = parsePostmanSpec(col);
        const info = col.info as Record<string, unknown> | undefined;
        if (!serverName && info?.name) setServerName(String(info.name));
      } else if (protocol === "graphql") {
        parsed = parseGraphQlSdl(specText);
      }
      if (parsed.length === 0) throw new Error("No operations found. Check the spec format and try again.");
      setTools(parsed); setStep(2);
    } catch (err) {
      setParseError(err instanceof Error ? err.message : "Failed to parse spec");
    } finally { setParsing(false); }
  }

  async function registerServer() {
    if (!token) return;
    const name = serverName.trim();
    if (!name) { setSaveError("Server name is required"); return; }
    if (selectedTools.length === 0) { setSaveError("Select at least one tool"); return; }
    setSaving(true); setSaveError(null);
    try {
      await api.createMcpServer(token, {
        name, category: serverCategory, status: "healthy",
        tool_names: selectedTools.map((t) => t.name),
        endpoint_url: endpointUrl.trim() || null,
        transport: "streamable_http",
        connection_config: {},
      });
      setSavedOk(true); onSaved();
      setTimeout(() => { handleClose(); }, 1800);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Failed to register server");
    } finally { setSaving(false); }
  }

  if (!open) return null;

  const PROTOCOL_OPTIONS: { id: Protocol; icon: React.ReactNode; label: string; desc: string }[] = [
    { id: "openapi_url",  icon: <Network className="h-5 w-5 text-blue-400" />,   label: "OpenAPI URL",          desc: "Fetch spec from a public or internal URL" },
    { id: "openapi_json", icon: <FileJson className="h-5 w-5 text-emerald-400" />, label: "Paste OpenAPI JSON",   desc: "Paste OpenAPI 3.x or Swagger 2.x JSON" },
    { id: "postman",      icon: <FileJson className="h-5 w-5 text-orange-400" />,  label: "Postman Collection",   desc: "Paste Postman Collection v2.1 JSON" },
    { id: "graphql",      icon: <Code2 className="h-5 w-5 text-pink-400" />,       label: "GraphQL SDL",          desc: "Paste GraphQL schema definition language" },
  ];

  const ROLE_OPTIONS = [
    { value: "tenant_admin",   label: "Tenant Admin" },
    { value: "security_admin", label: "Security Admin" },
    { value: "ai_user",        label: "AI User" },
    { value: "readonly_user",  label: "Read-Only" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={handleClose}>
      <div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-border bg-card shadow-2xl" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="sticky top-0 z-10 border-b border-border/60 bg-card/95 backdrop-blur px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/30">
                <Wand2 className="h-5 w-5 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-base font-semibold">REST to MCP Auto-Proxy Wizard</h2>
                <p className="text-xs text-muted-foreground">
                  Convert any REST API spec into a registered MCP server
                  <span className="ml-2 text-[10px] text-indigo-400 border border-indigo-400/30 bg-indigo-400/5 rounded px-1.5 py-0.5">BL-083</span>
                </p>
              </div>
            </div>
            <button type="button" className="rounded-lg border border-border/60 p-1.5 text-muted-foreground hover:text-foreground transition-colors" onClick={handleClose}>
              <X className="h-4 w-4" />
            </button>
          </div>
          {/* Step indicator */}
          <div className="flex items-center gap-1">
            <StepDot step={1} active={step === 1} done={step > 1} />
            <StepConnector done={step > 1} />
            <StepDot step={2} active={step === 2} done={step > 2} />
            <StepConnector done={step > 2} />
            <StepDot step={3} active={step === 3} done={savedOk} />
            <div className="ml-3 flex gap-4 text-xs text-muted-foreground">
              <span className={step === 1 ? "text-foreground font-medium" : ""}>Protocol</span>
              <span className={step === 2 ? "text-foreground font-medium" : ""}>Tool Preview</span>
              <span className={step === 3 ? "text-foreground font-medium" : ""}>Register</span>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-5">
          {/* ── STEP 1 ── */}
          {step === 1 && (
            <>
              <div>
                <p className="text-sm font-semibold mb-3">Select API spec format</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {PROTOCOL_OPTIONS.map((opt) => (
                    <button key={opt.id} type="button" onClick={() => setProtocol(opt.id)}
                      className={cn("flex items-start gap-3 rounded-xl border p-4 text-left transition-all", protocol === opt.id ? "border-primary/60 bg-primary/5" : "border-border/60 bg-card/50 hover:border-border/90")}>
                      <div className="mt-0.5 shrink-0">{opt.icon}</div>
                      <div>
                        <p className="text-sm font-medium">{opt.label}</p>
                        <p className="text-xs text-muted-foreground">{opt.desc}</p>
                      </div>
                      {protocol === opt.id && <Check className="h-4 w-4 text-primary ml-auto shrink-0 mt-0.5" />}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                {protocol === "openapi_url" && (
                  <>
                    <label className="text-sm font-medium" htmlFor="spec-url">OpenAPI spec URL</label>
                    <input id="spec-url" value={specUrl} onChange={(e) => setSpecUrl(e.target.value)}
                      placeholder="https://api.example.com/openapi.json"
                      className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-primary" />
                    <p className="text-xs text-muted-foreground">Must be accessible from your browser (JSON format preferred).</p>
                  </>
                )}
                {(protocol === "openapi_json" || protocol === "postman") && (
                  <>
                    <label className="text-sm font-medium" htmlFor="spec-text">
                      {protocol === "openapi_json" ? "OpenAPI JSON" : "Postman Collection JSON"}
                    </label>
                    <textarea id="spec-text" value={specText} onChange={(e) => setSpecText(e.target.value)} rows={10}
                      placeholder={protocol === "openapi_json" ? '{"openapi": "3.0.0", "paths": { ... }}' : '{"info": {...}, "item": [...]}'}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs outline-none focus:ring-1 focus:ring-primary" />
                  </>
                )}
                {protocol === "graphql" && (
                  <>
                    <label className="text-sm font-medium" htmlFor="spec-gql">GraphQL SDL</label>
                    <textarea id="spec-gql" value={specText} onChange={(e) => setSpecText(e.target.value)} rows={10}
                      placeholder={"type Query {\n  getUser(id: ID!): User\n}\ntype Mutation {\n  createUser(name: String!): User\n}"}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs outline-none focus:ring-1 focus:ring-primary" />
                  </>
                )}
              </div>

              {parseError && (
                <div className="flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                  <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-red-400">{parseError}</p>
                </div>
              )}

              <div className="flex justify-end pt-2">
                <Button className="gap-2" onClick={parseSpec} disabled={parsing}>
                  {parsing ? <><Loader2 className="h-4 w-4 animate-spin" /> Parsing spec…</> : <><ArrowRight className="h-4 w-4" /> Parse and preview tools</>}
                </Button>
              </div>
            </>
          )}

          {/* ── STEP 2 ── */}
          {step === 2 && (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold">Tool Preview</p>
                  <p className="text-xs text-muted-foreground">{tools.length} operations discovered · {selectedTools.length} selected</p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setTools((t) => t.map((tool) => ({ ...tool, selected: true })))}>Select all</Button>
                  <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setTools((t) => t.map((tool) => ({ ...tool, selected: false })))}>None</Button>
                </div>
              </div>

              <div className="space-y-1.5 max-h-80 overflow-y-auto pr-1">
                {tools.map((tool, i) => (
                  <div key={tool.name} className={cn("rounded-lg border transition-colors", tool.selected ? "border-border/60 bg-card/60" : "border-border/30 bg-muted/10 opacity-50")}>
                    <div className="flex items-center gap-3 px-3 py-2.5">
                      <input type="checkbox" checked={tool.selected} onChange={(e) => setTools((prev) => prev.map((t, j) => j === i ? { ...t, selected: e.target.checked } : t))} className="rounded" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <code className="text-xs font-mono font-medium text-foreground">{tool.name}</code>
                          {tool.method && (
                            <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded border",
                              tool.method === "GET" || tool.method === "QUERY" ? "text-blue-400 border-blue-400/30 bg-blue-400/5" :
                              tool.method === "DELETE" ? "text-red-400 border-red-400/30 bg-red-400/5" :
                              "text-amber-400 border-amber-400/30 bg-amber-400/5")}>
                              {tool.method}
                            </span>
                          )}
                          {tool.tags?.map((tag) => <Badge key={tag} variant="outline" className="text-[10px] py-0 h-4">{tag}</Badge>)}
                        </div>
                        {tool.path && <p className="text-[11px] text-muted-foreground font-mono truncate">{tool.path}</p>}
                      </div>
                      <button type="button" className="text-muted-foreground hover:text-foreground transition-colors shrink-0" onClick={() => setExpandedTool(expandedTool === tool.name ? null : tool.name)}>
                        {expandedTool === tool.name ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </button>
                    </div>
                    {expandedTool === tool.name && (
                      <div className="border-t border-border/40 px-3 py-2">
                        <p className="text-xs text-muted-foreground">{tool.description}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {selectedTools.length === 0 && <p className="text-xs text-amber-400 flex items-center gap-1.5"><AlertCircle className="h-3.5 w-3.5" /> Select at least one tool to continue</p>}

              <div className="flex justify-between pt-2">
                <Button variant="outline" className="gap-2" onClick={() => setStep(1)}><ArrowLeft className="h-4 w-4" /> Back</Button>
                <Button className="gap-2" disabled={selectedTools.length === 0} onClick={() => setStep(3)}><ArrowRight className="h-4 w-4" /> Configure server</Button>
              </div>
            </>
          )}

          {/* ── STEP 3 ── */}
          {step === 3 && (
            <>
              {savedOk ? (
                <div className="flex flex-col items-center gap-4 py-10">
                  <CheckCircle2 className="h-14 w-14 text-emerald-400" />
                  <div className="text-center">
                    <p className="text-lg font-semibold text-emerald-400">MCP Server Registered!</p>
                    <p className="text-sm text-muted-foreground mt-1"><strong>{serverName}</strong> added with {selectedTools.length} tools.</p>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-sm font-semibold">Server Configuration</p>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5 sm:col-span-2">
                      <label className="text-sm font-medium" htmlFor="wiz-name">Server name <span className="text-red-400">*</span></label>
                      <input id="wiz-name" value={serverName} onChange={(e) => setServerName(e.target.value)} placeholder="Payments API MCP"
                        className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-primary" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium" htmlFor="wiz-category">Category</label>
                      <input id="wiz-category" value={serverCategory} onChange={(e) => setServerCategory(e.target.value)} list="wiz-cat-list"
                        className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-primary" />
                      <datalist id="wiz-cat-list">{categories.map((c) => <option key={c} value={c} />)}</datalist>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium" htmlFor="wiz-endpoint">Base URL</label>
                      <input id="wiz-endpoint" value={endpointUrl} onChange={(e) => setEndpointUrl(e.target.value)} placeholder="https://api.example.com"
                        className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-primary" />
                    </div>
                  </div>

                  {/* RBAC */}
                  <div className="space-y-2 rounded-xl border border-border/60 bg-muted/10 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Shield className="h-4 w-4 text-indigo-400" />
                      <p className="text-sm font-medium">RBAC Access Groups</p>
                    </div>
                    <p className="text-xs text-muted-foreground">Which roles can call tools on this server via the gateway?</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {ROLE_OPTIONS.map((role) => {
                        const on = rbacGroups.includes(role.value);
                        return (
                          <button key={role.value} type="button"
                            onClick={() => setRbacGroups((prev) => on ? prev.filter((r) => r !== role.value) : [...prev, role.value])}
                            className={cn("flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all",
                              on ? "border-primary/60 bg-primary/10 text-foreground" : "border-border/60 bg-card/50 text-muted-foreground hover:border-border/90")}>
                            {on && <Check className="h-3 w-3 text-primary" />}
                            {role.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="rounded-xl border border-border/60 bg-muted/10 p-4 space-y-2">
                    <p className="text-xs font-semibold text-muted-foreground">SUMMARY</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div><p className="text-muted-foreground">Tools registered</p><p className="font-semibold">{selectedTools.length}</p></div>
                      <div><p className="text-muted-foreground">Protocol</p><p className="font-semibold capitalize">{protocol.replace(/_/g, " ")}</p></div>
                      <div><p className="text-muted-foreground">Transport</p><p className="font-semibold">Streamable HTTP</p></div>
                      <div><p className="text-muted-foreground">Roles</p><p className="font-semibold">{rbacGroups.length} group{rbacGroups.length !== 1 ? "s" : ""}</p></div>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Tools preview</p>
                      <div className="flex flex-wrap gap-1">
                        {selectedTools.slice(0, 8).map((t) => <code key={t.name} className="text-[10px] bg-muted/40 rounded px-1.5 py-0.5">{t.name}</code>)}
                        {selectedTools.length > 8 && <span className="text-[10px] text-muted-foreground">+{selectedTools.length - 8} more</span>}
                      </div>
                    </div>
                  </div>

                  {saveError && (
                    <div className="flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                      <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                      <p className="text-xs text-red-400">{saveError}</p>
                    </div>
                  )}

                  <div className="flex justify-between pt-2">
                    <Button variant="outline" className="gap-2" onClick={() => setStep(2)} disabled={saving}><ArrowLeft className="h-4 w-4" /> Back</Button>
                    <Button className="gap-2" onClick={registerServer} disabled={saving || !token}>
                      {saving ? <><Loader2 className="h-4 w-4 animate-spin" /> Registering…</> : <><Plus className="h-4 w-4" /> Register MCP server</>}
                    </Button>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
