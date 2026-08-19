"use client";

import { useEffect, useState } from "react";
import { Loader2, Plus, RotateCcw, Trash2 } from "lucide-react";
import { AppModal } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, ApiError, type ApiIacEvidenceCheckConfig, type ApiIacEvidenceConfig } from "@/lib/api";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2 disabled:opacity-50";
const labelClass = "text-sm font-medium";

function emptyCheck(): ApiIacEvidenceCheckConfig {
  return {
    id: "",
    title: "",
    framework: "",
    pattern: "",
    enabled: true,
  };
}

interface IacEvidenceConfigModalProps {
  open: boolean;
  token: string | null;
  canEdit: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function IacEvidenceConfigModal({ open, token, canEdit, onClose, onSaved }: IacEvidenceConfigModalProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<ApiIacEvidenceConfig | null>(null);
  const [scanPaths, setScanPaths] = useState<string[]>([]);
  const [checks, setChecks] = useState<ApiIacEvidenceCheckConfig[]>([]);

  useEffect(() => {
    if (!open || !token) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getIacEvidenceConfig(token!);
        if (!cancelled) {
          setConfig(data);
          setScanPaths(data.scan_paths);
          setChecks(data.checks);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Unable to load scanner configuration");
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

  function updateCheck(index: number, patch: Partial<ApiIacEvidenceCheckConfig>) {
    setChecks((current) => current.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  }

  async function handleSave() {
    if (!token || !canEdit) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateIacEvidenceConfig(token, { scan_paths: scanPaths, checks });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save configuration");
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    if (!token || !canEdit) return;
    setSaving(true);
    setError(null);
    try {
      const data = await api.resetIacEvidenceConfig(token);
      setConfig(data);
      setScanPaths(data.scan_paths);
      setChecks(data.checks);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reset configuration");
    } finally {
      setSaving(false);
    }
  }

  if (!open) return null;

  return (
    <AppModal
      title={canEdit ? "Configure IaC evidence scanner" : "IaC evidence scanner configuration"}
      description="Define manifest paths and pattern checks used for infrastructure evidence scans."
      onClose={onClose}
      size="2xl"
    >
      {loading && (
        <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading configuration…
        </div>
      )}

      {!loading && config && (
        <div className="space-y-6">
          <div className="rounded-lg border border-border/60 bg-muted/10 p-3 text-sm">
            <p className="font-medium">Deploy root (server)</p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">{config.deploy_root}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Set <code className="rounded bg-muted px-1">{config.deploy_root_env}</code> in the backend environment
              to point at your Helm/OPA manifests. Scan paths below are relative to this root.
            </p>
          </div>

          <section className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <p className={labelClass}>Scan paths</p>
              {canEdit && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={() => setScanPaths((current) => [...current, ""])}
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add path
                </Button>
              )}
            </div>
            <div className="space-y-2">
              {scanPaths.map((path, index) => (
                <div key={`path-${index}`} className="flex gap-2">
                  <input
                    className={inputClass}
                    value={path}
                    disabled={!canEdit}
                    placeholder="helm/pysetu/templates"
                    onChange={(e) =>
                      setScanPaths((current) => current.map((item, i) => (i === index ? e.target.value : item)))
                    }
                  />
                  {canEdit && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="shrink-0"
                      aria-label="Remove path"
                      onClick={() => setScanPaths((current) => current.filter((_, i) => i !== index))}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <p className={labelClass}>Control checks</p>
              {canEdit && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={() => setChecks((current) => [...current, emptyCheck()])}
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add check
                </Button>
              )}
            </div>
            <div className="space-y-3">
              {checks.map((check, index) => (
                <div key={`check-${index}`} className="rounded-lg border border-border/60 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                      <input
                        type="checkbox"
                        checked={check.enabled}
                        disabled={!canEdit}
                        onChange={(e) => updateCheck(index, { enabled: e.target.checked })}
                      />
                      Enabled
                    </label>
                    {canEdit && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        aria-label="Remove check"
                        onClick={() => setChecks((current) => current.filter((_, i) => i !== index))}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input
                      className={inputClass}
                      value={check.id}
                      disabled={!canEdit}
                      placeholder="IAC-OPA-001"
                      onChange={(e) => updateCheck(index, { id: e.target.value })}
                    />
                    <input
                      className={inputClass}
                      value={check.framework}
                      disabled={!canEdit}
                      placeholder="ISO 27001 A.8.9"
                      onChange={(e) => updateCheck(index, { framework: e.target.value })}
                    />
                    <input
                      className={`${inputClass} sm:col-span-2`}
                      value={check.title}
                      disabled={!canEdit}
                      placeholder="Check title"
                      onChange={(e) => updateCheck(index, { title: e.target.value })}
                    />
                    <input
                      className={`${inputClass} sm:col-span-2`}
                      value={check.pattern}
                      disabled={!canEdit}
                      placeholder="Pattern to search in manifests"
                      onChange={(e) => updateCheck(index, { pattern: e.target.value })}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          {config.is_customized && (
            <Badge variant="outline">Using tenant-customized rules</Badge>
          )}

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
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save configuration"}
              </Button>
            )}
          </div>
        </div>
      )}
    </AppModal>
  );
}
