import React from "react";

interface ApiKeyLimitsProps {
  limits: {
    ai_rate_limit_rpm: number | null;
    ai_rate_limit_rph: number | null;
    ai_rate_limit_rpd: number | null;
    ai_token_limit_tpm: number | null;
    ai_token_limit_tph: number | null;
    ai_token_limit_tpd: number | null;
    token_saving_enabled?: boolean | null;
    token_saving_mode?: string | null;
  };
  onChange: (field: string, value: number | null | boolean | string | null) => void;
  disabled?: boolean;
}

export function ApiKeyLimitsForm({ limits, onChange, disabled }: ApiKeyLimitsProps) {
  return (
    <div className="space-y-3 pt-2">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Gateway Limits (Optional)</p>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Rate Limits (Requests)</p>
          <div className="grid grid-cols-3 gap-2">
            <input
              type="number"
              min="0"
              placeholder="Per Min"
              title="Requests per Minute"
              value={limits.ai_rate_limit_rpm || ""}
              onChange={(e) => onChange("ai_rate_limit_rpm", e.target.value ? parseInt(e.target.value) : null)}
              disabled={disabled}
              className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
            />
            <input
              type="number"
              min="0"
              placeholder="Per Hr"
              title="Requests per Hour"
              value={limits.ai_rate_limit_rph || ""}
              onChange={(e) => onChange("ai_rate_limit_rph", e.target.value ? parseInt(e.target.value) : null)}
              disabled={disabled}
              className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
            />
            <input
              type="number"
              min="0"
              placeholder="Per Day"
              title="Requests per Day"
              value={limits.ai_rate_limit_rpd || ""}
              onChange={(e) => onChange("ai_rate_limit_rpd", e.target.value ? parseInt(e.target.value) : null)}
              disabled={disabled}
              className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
            />
          </div>
        </div>
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Token Limits</p>
          <div className="grid grid-cols-3 gap-2">
            <input
              type="number"
              min="0"
              placeholder="Per Min"
              title="Tokens per Minute"
              value={limits.ai_token_limit_tpm || ""}
              onChange={(e) => onChange("ai_token_limit_tpm", e.target.value ? parseInt(e.target.value) : null)}
              disabled={disabled}
              className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
            />
            <input
              type="number"
              min="0"
              placeholder="Per Hr"
              title="Tokens per Hour"
              value={limits.ai_token_limit_tph || ""}
              onChange={(e) => onChange("ai_token_limit_tph", e.target.value ? parseInt(e.target.value) : null)}
              disabled={disabled}
              className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
            />
            <input
              type="number"
              min="0"
              placeholder="Per Day"
              title="Tokens per Day"
              value={limits.ai_token_limit_tpd || ""}
              onChange={(e) => onChange("ai_token_limit_tpd", e.target.value ? parseInt(e.target.value) : null)}
              disabled={disabled}
              className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
            />
          </div>
        </div>
      </div>

      <div className="space-y-2 rounded-md border border-border/60 bg-muted/10 p-3">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Token Saving</p>
        <p className="text-xs text-muted-foreground">
          Ingress compression for this API key. Converts JSON to TOON and strips markdown from user messages.
        </p>
        <select
          value={
            limits.token_saving_enabled === null || limits.token_saving_enabled === undefined
              ? ""
              : limits.token_saving_enabled
                ? limits.token_saving_mode || "both"
                : "off"
          }
          onChange={(e) => {
            const value = e.target.value;
            if (value === "") {
              onChange("token_saving_enabled", null);
              onChange("token_saving_mode", null);
            } else if (value === "off") {
              onChange("token_saving_enabled", false);
              onChange("token_saving_mode", null);
            } else {
              onChange("token_saving_enabled", true);
              onChange("token_saving_mode", value);
            }
          }}
          disabled={disabled}
          className="flex h-8 w-full max-w-md rounded-md border border-input bg-background px-2 text-xs"
        >
          <option value="">Inherit tenant default</option>
          <option value="off">Disabled for this key</option>
          <option value="both">Enabled — JSON→TOON + strip markdown</option>
          <option value="json_to_toon">Enabled — JSON→TOON only</option>
          <option value="strip_markdown">Enabled — strip markdown only</option>
        </select>
      </div>
    </div>
  );
}
