import React from "react";

interface ApiKeyLimitsProps {
  limits: {
    ai_rate_limit_rpm: number | null;
    ai_rate_limit_rph: number | null;
    ai_rate_limit_rpd: number | null;
    ai_token_limit_tpm: number | null;
    ai_token_limit_tph: number | null;
    ai_token_limit_tpd: number | null;
  };
  onChange: (field: string, value: number | null) => void;
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
    </div>
  );
}
