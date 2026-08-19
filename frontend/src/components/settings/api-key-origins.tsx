import React from "react";

export type ApiKeyOriginsMode = "inherit" | "allow_all" | "restrict";

export function originsModeFromKey(
  mode: ApiKeyOriginsMode | undefined,
  origins: string[] | null | undefined
): ApiKeyOriginsMode {
  if (mode) return mode;
  if (origins === null || origins === undefined) return "inherit";
  if (origins.length === 0) return "allow_all";
  return "restrict";
}

export function originsToPayload(mode: ApiKeyOriginsMode, text: string): string[] | null {
  if (mode === "inherit") return null;
  if (mode === "allow_all") return [];
  return text
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);
}

export function originsLabel(
  mode: ApiKeyOriginsMode,
  origins: string[] | null | undefined,
  tenantOriginCount?: number
): string {
  if (mode === "inherit") {
    if (tenantOriginCount && tenantOriginCount > 0) {
      return `Inherit tenant (${tenantOriginCount} host${tenantOriginCount === 1 ? "" : "s"})`;
    }
    return "Inherit tenant (any origin)";
  }
  if (mode === "allow_all") return "Allow any origin";
  if (origins?.length) return origins.join(", ");
  return "Restrict (not set)";
}

interface ApiKeyOriginsFormProps {
  mode: ApiKeyOriginsMode;
  originsText: string;
  onModeChange: (mode: ApiKeyOriginsMode) => void;
  onOriginsTextChange: (text: string) => void;
  disabled?: boolean;
}

export function ApiKeyOriginsForm({
  mode,
  originsText,
  onModeChange,
  onOriginsTextChange,
  disabled,
}: ApiKeyOriginsFormProps) {
  return (
    <div className="space-y-2 rounded-md border border-border/60 bg-muted/10 p-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Allowed API Origins</p>
      <p className="text-xs text-muted-foreground">
        Restrict browser requests that send an <code className="text-[11px]">Origin</code> header. Server-to-server
        calls without Origin are always allowed when no restriction applies.
      </p>
      <select
        value={mode}
        onChange={(e) => onModeChange(e.target.value as ApiKeyOriginsMode)}
        disabled={disabled}
        className="flex h-8 w-full max-w-md rounded-md border border-input bg-background px-2 text-xs"
      >
        <option value="inherit">Inherit tenant default</option>
        <option value="allow_all">Allow any origin (override)</option>
        <option value="restrict">Restrict to list</option>
      </select>
      {mode === "restrict" && (
        <textarea
          value={originsText}
          onChange={(e) => onOriginsTextChange(e.target.value)}
          disabled={disabled}
          placeholder="https://app.example.com, https://admin.example.com"
          rows={2}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs"
        />
      )}
    </div>
  );
}
