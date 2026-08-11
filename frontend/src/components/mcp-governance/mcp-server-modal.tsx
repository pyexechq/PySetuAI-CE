"use client";

import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError, api, type ApiMcpServer, type ApiMcpServerCreateRequest, type ApiMcpServerUpdateRequest } from "@/lib/api";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50";
const labelClass = "text-sm font-medium";

const MCP_TRANSPORTS = [
  { value: "sse", label: "SSE (Server-Sent Events)" },
  { value: "streamable_http", label: "Streamable HTTP" },
  { value: "stdio", label: "Stdio (local process)" },
];

const MCP_STATUSES = [
  { value: "healthy", label: "Healthy" },
  { value: "degraded", label: "Degraded" },
  { value: "offline", label: "Offline" },
];

const DEFAULT_CATEGORIES = ["Human Resources", "Finance", "Sales", "Productivity", "Engineering", "Operations"];

function ModalShell({
  title,
  description,
  onClose,
  children,
}: {
  title: string;
  description?: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">{title}</h2>
            {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
          </div>
          <Button variant="outline" size="sm" className="h-8 w-8 p-0" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}

function parseToolNames(value: string): string[] {
  return value
    .split(/[,;\n]+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

interface McpToolSchema {
  name: string;
  description?: string | null;
  inputSchema?: Record<string, unknown> | null;
}

function parseToolSchemas(value: unknown): McpToolSchema[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    .map((item) => ({
      name: String(item.name ?? ""),
      description: typeof item.description === "string" ? item.description : null,
      inputSchema:
        item.inputSchema && typeof item.inputSchema === "object"
          ? (item.inputSchema as Record<string, unknown>)
          : item.input_schema && typeof item.input_schema === "object"
            ? (item.input_schema as Record<string, unknown>)
            : null,
    }))
    .filter((item) => item.name);
}

function exampleArgsFromSchema(schema: Record<string, unknown> | null | undefined): string {
  if (!schema || typeof schema !== "object") return "{}";
  const properties = schema.properties;
  if (!properties || typeof properties !== "object") return "{}";

  const example: Record<string, unknown> = {};
  for (const [key, prop] of Object.entries(properties as Record<string, unknown>)) {
    if (prop && typeof prop === "object" && "default" in prop) {
      example[key] = (prop as { default?: unknown }).default;
      continue;
    }
    const type = prop && typeof prop === "object" ? (prop as { type?: string | string[] }).type : undefined;
    const primaryType = Array.isArray(type) ? type[0] : type;
    if (primaryType === "string") example[key] = "";
    else if (primaryType === "number" || primaryType === "integer") example[key] = 0;
    else if (primaryType === "boolean") example[key] = false;
    else if (primaryType === "array") example[key] = [];
    else example[key] = null;
  }
  return JSON.stringify(example, null, 2);
}

interface McpServerModalProps {
  open: boolean;
  server: ApiMcpServer | null;
  token: string | null;
  categorySuggestions: string[];
  onClose: () => void;
  onSaved: () => void;
}

export function McpServerModal({
  open,
  server,
  token,
  categorySuggestions,
  onClose,
  onSaved,
}: McpServerModalProps) {
  const isEdit = server !== null;
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("healthy");
  const [toolNamesText, setToolNamesText] = useState("");
  const [endpointUrl, setEndpointUrl] = useState("");
  const [transport, setTransport] = useState("sse");
  const [authHeader, setAuthHeader] = useState("");
  const [timeoutSec, setTimeoutSec] = useState("30");
  const [error, setError] = useState<string | null>(null);
  const [healthMessage, setHealthMessage] = useState<string | null>(null);
  const [discoverMessage, setDiscoverMessage] = useState<string | null>(null);
  const [invokeToolName, setInvokeToolName] = useState("");
  const [invokeArgsJson, setInvokeArgsJson] = useState("{}");
  const [invokeMessage, setInvokeMessage] = useState<string | null>(null);
  const [invokeResultJson, setInvokeResultJson] = useState<string | null>(null);
  const [toolSchemas, setToolSchemas] = useState<McpToolSchema[]>([]);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [invoking, setInvoking] = useState(false);

  const categories = Array.from(new Set([...DEFAULT_CATEGORIES, ...categorySuggestions])).sort();

  useEffect(() => {
    if (!open) return;
    setName(server?.name ?? "");
    setCategory(server?.category ?? "");
    setStatus(server?.status ?? "healthy");
    setToolNamesText((server?.tool_names ?? []).join(", "));
    setEndpointUrl(server?.endpoint_url ?? "");
    setTransport(server?.transport ?? "sse");
    setAuthHeader(server?.connection_config?.auth_header ?? "");
    setTimeoutSec(String(server?.connection_config?.timeout_sec ?? 30));
    setError(null);
    setHealthMessage(null);
    setDiscoverMessage(null);
    const schemas = parseToolSchemas(server?.connection_config?.tool_schemas);
    setToolSchemas(schemas);
    const tools = server?.tool_names ?? [];
    const initialTool = tools[0] ?? schemas[0]?.name ?? "";
    setInvokeToolName(initialTool);
    setInvokeArgsJson(exampleArgsFromSchema(schemas.find((item) => item.name === initialTool)?.inputSchema));
    setInvokeMessage(null);
    setInvokeResultJson(null);
  }, [open, server]);

  if (!open) return null;

  const selectedToolSchema = toolSchemas.find((item) => item.name === invokeToolName.trim());

  function applySchemaTemplate() {
    setInvokeArgsJson(exampleArgsFromSchema(selectedToolSchema?.inputSchema));
  }

  function handleInvokeToolChange(nextTool: string) {
    setInvokeToolName(nextTool);
    const schema = toolSchemas.find((item) => item.name === nextTool.trim());
    if (schema?.inputSchema) {
      setInvokeArgsJson(exampleArgsFromSchema(schema.inputSchema));
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;

    const trimmedName = name.trim();
    const trimmedCategory = category.trim();
    if (!trimmedName) {
      setError("Server name is required");
      return;
    }
    if (!trimmedCategory) {
      setError("Category is required");
      return;
    }

    const tool_names = parseToolNames(toolNamesText);
    const connection_config = {
      ...(authHeader.trim() ? { auth_header: authHeader.trim() } : {}),
      timeout_sec: Number(timeoutSec) || 30,
    };

    setSaving(true);
    setError(null);

    try {
      if (isEdit && server) {
        const body: ApiMcpServerUpdateRequest = {
          name: trimmedName,
          category: trimmedCategory,
          status,
          tool_names,
          endpoint_url: endpointUrl.trim() || null,
          transport,
          connection_config,
        };
        await api.updateMcpServer(token, server.id, body);
      } else {
        const body: ApiMcpServerCreateRequest = {
          name: trimmedName,
          category: trimmedCategory,
          status,
          tool_names,
          endpoint_url: endpointUrl.trim() || null,
          transport,
          connection_config,
        };
        await api.createMcpServer(token, body);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save MCP server");
    } finally {
      setSaving(false);
    }
  }

  async function testConnection() {
    if (!token || !server) return;

    setTesting(true);
    setError(null);
    setHealthMessage(null);

    try {
      if (isEdit) {
        const body: ApiMcpServerUpdateRequest = {
          endpoint_url: endpointUrl.trim() || null,
          transport,
          connection_config: {
            ...(authHeader.trim() ? { auth_header: authHeader.trim() } : {}),
            timeout_sec: Number(timeoutSec) || 30,
          },
        };
        await api.updateMcpServer(token, server.id, body);
      }

      const result = await api.checkMcpServerHealth(token, server.id);
      const prefix = result.ok ? "✓" : result.skipped ? "ℹ" : "✗";
      setHealthMessage(`${prefix} ${result.message}${result.latency_ms ? ` (${result.latency_ms}ms)` : ""}`);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Connection test failed");
    } finally {
      setTesting(false);
    }
  }

  async function invokeRegisteredTool() {
    if (!token || !server) return;

    const trimmedName = invokeToolName.trim();
    if (!trimmedName) {
      setError("Select or enter a tool name to invoke");
      return;
    }

    let argumentsPayload: Record<string, unknown> = {};
    const trimmedArgs = invokeArgsJson.trim();
    if (trimmedArgs) {
      try {
        const parsed = JSON.parse(trimmedArgs) as unknown;
        if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
          argumentsPayload = parsed as Record<string, unknown>;
        } else {
          setError("Tool arguments must be a JSON object");
          return;
        }
      } catch {
        setError("Tool arguments must be valid JSON");
        return;
      }
    }

    setInvoking(true);
    setError(null);
    setInvokeMessage(null);
    setInvokeResultJson(null);

    try {
      const result = await api.invokeMcpServerTool(token, server.id, {
        tool_name: trimmedName,
        arguments: argumentsPayload,
      });
      const prefix = result.ok ? "✓" : result.skipped ? "ℹ" : "✗";
      const sessionNote = result.session_reused ? " (session reused)" : "";
      setInvokeMessage(
        `${prefix} ${result.message}${result.latency_ms ? ` (${result.latency_ms}ms)` : ""}${sessionNote}`,
      );
      if (result.result) {
        setInvokeResultJson(JSON.stringify(result.result, null, 2));
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Tool invocation failed");
    } finally {
      setInvoking(false);
    }
  }

  async function discoverToolsFromEndpoint() {
    if (!token || !server) return;

    setDiscovering(true);
    setError(null);
    setDiscoverMessage(null);

    try {
      const body: ApiMcpServerUpdateRequest = {
        endpoint_url: endpointUrl.trim() || null,
        transport,
        connection_config: {
          ...(authHeader.trim() ? { auth_header: authHeader.trim() } : {}),
          timeout_sec: Number(timeoutSec) || 30,
        },
      };
      await api.updateMcpServer(token, server.id, body);

      const result = await api.discoverMcpServerTools(token, server.id);
      const prefix = result.ok ? "✓" : result.skipped ? "ℹ" : "✗";
      setDiscoverMessage(`${prefix} ${result.message}`);
      if (result.ok && result.tool_names.length > 0) {
        setToolNamesText(result.tool_names.join(", "));
      }
      if (result.tool_schemas?.length) {
        setToolSchemas(result.tool_schemas);
        const nextTool = result.tool_names[0] ?? result.tool_schemas[0]?.name ?? invokeToolName;
        if (nextTool) {
          setInvokeToolName(nextTool);
          const schema = result.tool_schemas.find((item) => item.name === nextTool);
          if (schema?.inputSchema) {
            setInvokeArgsJson(exampleArgsFromSchema(schema.inputSchema));
          }
        }
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Tool discovery failed");
    } finally {
      setDiscovering(false);
    }
  }

  const registeredTools = parseToolNames(toolNamesText);
  const toolSelectOptions = Array.from(new Set([...registeredTools, invokeToolName.trim()].filter(Boolean)));

  return (
    <ModalShell
      title={isEdit ? "Edit MCP Server" : "Register MCP Server"}
      description={
        isEdit
          ? "Update server metadata, MCP connection settings, and registered tools."
          : "Register an MCP server with SSE/HTTP transport and tool catalog."
      }
      onClose={onClose}
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-1.5">
          <label className={labelClass} htmlFor="mcp-name">
            Server name
          </label>
          <input
            id="mcp-name"
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="HR Database MCP"
            disabled={saving}
          />
        </div>

        <div className="space-y-1.5">
          <label className={labelClass} htmlFor="mcp-category">
            Category
          </label>
          <input
            id="mcp-category"
            className={inputClass}
            list="mcp-category-suggestions"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="Finance"
            disabled={saving}
          />
          <datalist id="mcp-category-suggestions">
            {categories.map((cat) => (
              <option key={cat} value={cat} />
            ))}
          </datalist>
        </div>

        <div className="space-y-1.5">
          <label className={labelClass} htmlFor="mcp-status">
            Status
          </label>
          <select
            id="mcp-status"
            className={inputClass}
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            disabled={saving}
          >
            {MCP_STATUSES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-lg border border-border/60 bg-muted/10 p-3 space-y-3">
          <p className="text-sm font-medium">MCP connection</p>

          <div className="space-y-1.5">
            <label className={labelClass} htmlFor="mcp-transport">
              Transport
            </label>
            <select
              id="mcp-transport"
              className={inputClass}
              value={transport}
              onChange={(e) => setTransport(e.target.value)}
              disabled={saving}
            >
              {MCP_TRANSPORTS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className={labelClass} htmlFor="mcp-endpoint">
              Endpoint URL
            </label>
            <input
              id="mcp-endpoint"
              className={inputClass}
              value={endpointUrl}
              onChange={(e) => setEndpointUrl(e.target.value)}
              placeholder="https://mcp.example.com/sse"
              disabled={saving || transport === "stdio"}
            />
            <p className="text-xs text-muted-foreground">
              SSE endpoint for remote servers. Not used for stdio transport.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <label className={labelClass} htmlFor="mcp-auth">
                Authorization header
              </label>
              <input
                id="mcp-auth"
                type="password"
                className={inputClass}
                value={authHeader}
                onChange={(e) => setAuthHeader(e.target.value)}
                placeholder="Bearer mcp_…"
                disabled={saving}
              />
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="mcp-timeout">
                Timeout (seconds)
              </label>
              <input
                id="mcp-timeout"
                type="number"
                min={5}
                max={120}
                className={inputClass}
                value={timeoutSec}
                onChange={(e) => setTimeoutSec(e.target.value)}
                disabled={saving}
              />
            </div>
          </div>
        </div>

        <div className="space-y-1.5">
          <label className={labelClass} htmlFor="mcp-tools">
            Registered tools
          </label>
          <textarea
            id="mcp-tools"
            className="min-h-[88px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none disabled:opacity-50"
            value={toolNamesText}
            onChange={(e) => setToolNamesText(e.target.value)}
            placeholder="query, create_ticket, lookup_employee"
            disabled={saving}
          />
          <p className="text-xs text-muted-foreground">
            Comma or newline separated. Tool count updates automatically ({parseToolNames(toolNamesText).length} tools).
          </p>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}
        {healthMessage && (
          <p className={`text-sm ${healthMessage.startsWith("✓") ? "text-emerald-400" : "text-muted-foreground"}`}>
            {healthMessage}
          </p>
        )}
        {discoverMessage && (
          <p className={`text-sm ${discoverMessage.startsWith("✓") ? "text-emerald-400" : "text-muted-foreground"}`}>
            {discoverMessage}
          </p>
        )}

        {isEdit && server && (
          <div className="rounded-lg border border-border/60 bg-muted/10 p-3 space-y-3">
            <p className="text-sm font-medium">Test tool invocation</p>
            <p className="text-xs text-muted-foreground">
              Calls tools/call on the MCP endpoint using the active session when available.
            </p>

            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="mcp-invoke-tool">
                Tool name
              </label>
              {toolSelectOptions.length > 0 ? (
                <select
                  id="mcp-invoke-tool"
                  className={inputClass}
                  value={invokeToolName}
                  onChange={(e) => handleInvokeToolChange(e.target.value)}
                  disabled={saving || invoking || transport === "stdio"}
                >
                  {toolSelectOptions.map((tool) => (
                    <option key={tool} value={tool}>
                      {tool}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id="mcp-invoke-tool"
                  className={inputClass}
                  value={invokeToolName}
                  onChange={(e) => setInvokeToolName(e.target.value)}
                  placeholder="query"
                  disabled={saving || invoking || transport === "stdio"}
                />
              )}
            </div>

            {selectedToolSchema?.description && (
              <p className="text-xs text-muted-foreground">{selectedToolSchema.description}</p>
            )}
            {selectedToolSchema?.inputSchema && (
              <pre className="max-h-28 overflow-auto rounded-md border border-border/60 bg-background p-2 text-[11px] text-muted-foreground">
                {JSON.stringify(selectedToolSchema.inputSchema, null, 2)}
              </pre>
            )}

            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <label className={labelClass} htmlFor="mcp-invoke-args">
                  Arguments (JSON)
                </label>
                {selectedToolSchema?.inputSchema && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    disabled={saving || invoking || transport === "stdio"}
                    onClick={applySchemaTemplate}
                  >
                    Fill from schema
                  </Button>
                )}
              </div>
              <textarea
                id="mcp-invoke-args"
                className="min-h-[72px] w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs outline-none disabled:opacity-50"
                value={invokeArgsJson}
                onChange={(e) => setInvokeArgsJson(e.target.value)}
                placeholder='{"query": "example"}'
                disabled={saving || invoking || transport === "stdio"}
              />
            </div>

            <Button
              type="button"
              variant="outline"
              className="w-full sm:w-auto"
              disabled={saving || testing || discovering || invoking || !token || transport === "stdio"}
              onClick={invokeRegisteredTool}
            >
              {invoking ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Invoking…
                </>
              ) : (
                "Invoke tool"
              )}
            </Button>

            {invokeMessage && (
              <p className={`text-sm ${invokeMessage.startsWith("✓") ? "text-emerald-400" : "text-muted-foreground"}`}>
                {invokeMessage}
              </p>
            )}
            {invokeResultJson && (
              <pre className="max-h-40 overflow-auto rounded-md border border-border/60 bg-background p-2 text-xs text-muted-foreground">
                {invokeResultJson}
              </pre>
            )}
          </div>
        )}

        <div className="flex flex-wrap justify-end gap-2 pt-2">
          {isEdit && server && (
            <>
              <Button
                type="button"
                variant="outline"
                disabled={saving || testing || discovering || invoking || !token || transport === "stdio"}
                onClick={testConnection}
              >
                {testing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Testing…
                  </>
                ) : (
                  "Test connection"
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={saving || testing || discovering || invoking || !token || transport === "stdio"}
                onClick={discoverToolsFromEndpoint}
              >
                {discovering ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Discovering…
                  </>
                ) : (
                  "Discover tools"
                )}
              </Button>
            </>
          )}
          <Button type="button" variant="outline" onClick={onClose} disabled={saving || testing || discovering || invoking}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving || testing || discovering || invoking || !token}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving…
              </>
            ) : isEdit ? (
              "Save changes"
            ) : (
              "Register server"
            )}
          </Button>
        </div>
      </form>
    </ModalShell>
  );
}
