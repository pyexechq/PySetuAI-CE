"use client";

import { useEffect, useState } from "react";
import { Loader2, RotateCcw } from "lucide-react";
import { AppModal } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, ApiError, type ApiDataMovementPolicyConfig } from "@/lib/api";

const labelClass = "text-sm font-medium";

interface DataMovementPolicyModalProps {
  open: boolean;
  token: string | null;
  canEdit: boolean;
  onClose: () => void;
  onSaved: () => void;
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

export function DataMovementPolicyModal({ open, token, canEdit, onClose, onSaved }: DataMovementPolicyModalProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<ApiDataMovementPolicyConfig | null>(null);
  const [restrictedLabels, setRestrictedLabels] = useState<string[]>([]);
  const [vectorDestinations, setVectorDestinations] = useState<string[]>([]);
  const [neverExemptLabels, setNeverExemptLabels] = useState<string[]>([]);

  useEffect(() => {
    if (!open || !token) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getDataMovementPolicy(token!);
        if (!cancelled) {
          setConfig(data);
          setRestrictedLabels(data.policy.restricted_labels);
          setVectorDestinations(data.policy.vector_destinations);
          setNeverExemptLabels(data.policy.never_exempt_labels);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Unable to load data-movement policy");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [open, token]);

  async function handleSave() {
    if (!token || !canEdit) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateDataMovementPolicy(token, {
        policy: {
          restricted_labels: restrictedLabels,
          vector_destinations: vectorDestinations,
          never_exempt_labels: neverExemptLabels,
        },
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save data-movement policy");
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    if (!token || !canEdit) return;
    setSaving(true);
    setError(null);
    try {
      const data = await api.resetDataMovementPolicy(token);
      setConfig(data);
      setRestrictedLabels(data.policy.restricted_labels);
      setVectorDestinations(data.policy.vector_destinations);
      setNeverExemptLabels(data.policy.never_exempt_labels);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reset data-movement policy");
    } finally {
      setSaving(false);
    }
  }

  if (!open) return null;

  return (
    <AppModal
      title={canEdit ? "Configure data-movement policy" : "Data-movement policy"}
      description="Define which sensitivity labels cannot reach vector destinations. OPA enforces these rules during governed RAG ingest."
      onClose={onClose}
      size="2xl"
    >
      {loading && (
        <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading policy…
        </div>
      )}

      {!loading && config && (
        <div className="space-y-6">
          <div className="rounded-lg border border-border/60 bg-muted/10 p-3 text-sm">
            <p className="font-medium">OPA policy package</p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">{config.opa_policy_path}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Tenant rules override the built-in defaults in <code className="rounded bg-muted px-1">gateway.rego</code> when saved.
              Policy Studio covers ingress prompt rules — not vector data movement.
            </p>
          </div>

          <section className="space-y-3">
            <p className={labelClass}>Blocked sensitivity labels</p>
            <p className="text-xs text-muted-foreground">
              Content with these labels cannot be sent to the protected destinations below.
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {config.label_options.map((option) => (
                <label key={option.id} className="flex items-center gap-2 rounded-md border border-border/60 px-3 py-2 text-sm">
                  <input
                    type="checkbox"
                    disabled={!canEdit}
                    checked={restrictedLabels.includes(option.id)}
                    onChange={() => setRestrictedLabels((current) => toggleValue(current, option.id))}
                  />
                  <span>{option.label}</span>
                  <Badge variant="outline" className="ml-auto font-mono text-[10px]">
                    {option.id}
                  </Badge>
                </label>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <p className={labelClass}>Protected destinations</p>
            <p className="text-xs text-muted-foreground">Vector pipeline hops where restricted labels are enforced.</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {config.destination_options.map((option) => (
                <label key={option.id} className="flex items-center gap-2 rounded-md border border-border/60 px-3 py-2 text-sm">
                  <input
                    type="checkbox"
                    disabled={!canEdit}
                    checked={vectorDestinations.includes(option.id)}
                    onChange={() => setVectorDestinations((current) => toggleValue(current, option.id))}
                  />
                  <span>{option.label}</span>
                  <Badge variant="outline" className="ml-auto font-mono text-[10px]">
                    {option.id}
                  </Badge>
                </label>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <p className={labelClass}>Never exempt labels</p>
            <p className="text-xs text-muted-foreground">
              Break-glass exemptions cannot override these labels, even for embedding hops.
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {config.label_options.map((option) => (
                <label key={`never-${option.id}`} className="flex items-center gap-2 rounded-md border border-border/60 px-3 py-2 text-sm">
                  <input
                    type="checkbox"
                    disabled={!canEdit}
                    checked={neverExemptLabels.includes(option.id)}
                    onChange={() => setNeverExemptLabels((current) => toggleValue(current, option.id))}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </section>

          {config.is_customized && <Badge variant="outline">Using tenant-customized policy</Badge>}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex flex-wrap justify-end gap-2">
            {canEdit && (
              <Button type="button" variant="outline" className="gap-1.5" disabled={saving} onClick={() => void handleReset()}>
                <RotateCcw className="h-4 w-4" />
                Reset defaults
              </Button>
            )}
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            {canEdit && (
              <Button type="button" disabled={saving} onClick={() => void handleSave()}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save policy"}
              </Button>
            )}
          </div>
        </div>
      )}
    </AppModal>
  );
}
