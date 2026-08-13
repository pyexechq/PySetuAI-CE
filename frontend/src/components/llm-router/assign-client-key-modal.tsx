"use client";

import { useState } from "react";
import { Check, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ApiError, api, type ApiClientApiKey } from "@/lib/api";

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

interface AssignClientKeyModalProps {
  open: boolean;
  rule: { name: string; responseFormat: string } | null;
  clientApiKeys: ApiClientApiKey[];
  token: string | null;
  onClose: () => void;
  onAssigned: () => void;
}

export function AssignClientKeyModal({
  open,
  rule,
  clientApiKeys,
  token,
  onClose,
  onAssigned,
}: AssignClientKeyModalProps) {
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!open || !rule) return null;

  const activeKeys = clientApiKeys.filter((k) => k.is_active);

  async function handleAssign(key: ApiClientApiKey) {
    if (!token || !rule) return;
    setError(null);
    setPendingId(key.id);
    try {
      await api.updateClientApiKey(token, key.id, { client_response_protocol: rule.responseFormat });
      onAssigned();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to assign key");
    } finally {
      setPendingId(null);
    }
  }

  async function handleUnassign(key: ApiClientApiKey) {
    if (!token) return;
    setError(null);
    setPendingId(key.id);
    try {
      await api.updateClientApiKey(token, key.id, { client_response_protocol: null });
      onAssigned();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to unassign key");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <ModalShell
      title="Assign API Key"
      description={`Choose which client API keys should receive the "${rule.responseFormat}" response format for "${rule.name}".`}
      onClose={onClose}
    >
      <div className="space-y-2">
        {activeKeys.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No active client API keys found. Create keys in Settings → API Keys.
          </p>
        ) : (
          activeKeys.map((key) => {
            const isAssigned = key.client_response_protocol === rule.responseFormat;
            const isPending = pendingId === key.id;
            return (
              <div
                key={key.id}
                className="flex items-center justify-between gap-2 rounded-md border border-border/60 bg-muted/20 px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{key.name}</p>
                  <p className="truncate font-mono text-xs text-muted-foreground">{key.key_masked}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {isAssigned && (
                    <Badge variant="success" className="text-[10px]">assigned</Badge>
                  )}
                  <Button
                    type="button"
                    size="sm"
                    variant={isAssigned ? "outline" : "default"}
                    className="h-8 gap-1.5 text-xs"
                    disabled={isPending}
                    onClick={() => (isAssigned ? handleUnassign(key) : handleAssign(key))}
                  >
                    {isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : isAssigned ? (
                      "Remove"
                    ) : (
                      <>
                        <Check className="h-3.5 w-3.5" /> Assign
                      </>
                    )}
                  </Button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

      <div className="mt-4 flex justify-end">
        <Button type="button" variant="outline" onClick={onClose}>
          Done
        </Button>
      </div>
    </ModalShell>
  );
}
