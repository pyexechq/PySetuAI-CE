"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ApiError, api, type ApiReportQuery, type ApiReportQueryTemplate } from "@/lib/api";
import type { ReportCatalogEntry } from "@/lib/types/domain";
import {
  getQueryTemplateForSource,
  resolveReportQueryTemplates,
} from "@/lib/report-query-templates";
import { useAuthStore } from "@/stores/auth-store";

type ModalMode = "create" | "query" | "schedule";

interface ReportManagementModalsProps {
  mode: ModalMode | null;
  report: ReportCatalogEntry | null;
  templates: ApiReportQueryTemplate[];
  token: string | null;
  canEdit: boolean;
  onClose: () => void;
  onSaved: () => void;
}

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
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl"
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

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50";
const labelClass = "text-sm font-medium";

const FREQUENCIES = [
  { value: "on_demand", label: "On demand" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
];

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function parseRecipientInput(value: string): string[] {
  return value
    .split(/[,;\n]+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function formatRecipientInput(recipients: string[]): string {
  return recipients.join(", ");
}

function toggleRecipient(current: string[], email: string): string[] {
  const normalized = email.toLowerCase();
  if (current.some((item) => item.toLowerCase() === normalized)) {
    return current.filter((item) => item.toLowerCase() !== normalized);
  }
  return [...current, email];
}

function QueryBuilder({
  source,
  filters,
  limit,
  templates,
  templatesLoading,
  onChange,
}: {
  source: string;
  filters: Record<string, unknown>;
  limit: number;
  templates: ApiReportQueryTemplate[];
  templatesLoading?: boolean;
  onChange: (query: ApiReportQuery) => void;
}) {
  const resolvedTemplates = resolveReportQueryTemplates(templates);
  const template = getQueryTemplateForSource(source, resolvedTemplates);

  function updateFilter(key: string, value: unknown) {
    const next = { ...filters };
    if (value === "" || value === null || (Array.isArray(value) && value.length === 0)) {
      delete next[key];
    } else {
      next[key] = value;
    }
    onChange({ source, filters: next, limit });
  }

  function toggleMulti(key: string, option: string) {
    const current = (filters[key] as string[] | undefined) ?? [];
    const next = current.includes(option) ? current.filter((v) => v !== option) : [...current, option];
    updateFilter(key, next);
  }

  if (!template) {
    return (
      <p className="text-sm text-muted-foreground">
        {templatesLoading ? "Loading query templates…" : "Unknown data source. Select a supported source below."}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className={labelClass}>Data source</label>
        <select
          className={inputClass}
          value={source}
          onChange={(e) => onChange({ source: e.target.value, filters: {}, limit })}
        >
          {resolvedTemplates.map((t) => (
            <option key={t.source} value={t.source}>
              {t.label}
            </option>
          ))}
        </select>
        <p className="text-xs text-muted-foreground">{template.description}</p>
      </div>

      {template.filter_fields.map((field) => (
        <div key={field.key} className="space-y-2">
          <label className={labelClass}>{field.label}</label>
          {field.type === "number" && (
            <input
              type="number"
              className={inputClass}
              value={(filters[field.key] as number | undefined) ?? (field.default as number | undefined) ?? ""}
              onChange={(e) => updateFilter(field.key, e.target.value ? Number(e.target.value) : null)}
            />
          )}
          {field.type === "text" && (
            <input
              type="text"
              className={inputClass}
              value={(filters[field.key] as string | undefined) ?? ""}
              onChange={(e) => updateFilter(field.key, e.target.value)}
            />
          )}
          {field.type === "multi_select" && field.options && (
            <div className="flex flex-wrap gap-2">
              {field.options.map((option) => {
                const selected = ((filters[field.key] as string[] | undefined) ?? []).includes(option);
                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() => toggleMulti(field.key, option)}
                    className={`rounded-md border px-2.5 py-1 text-xs capitalize ${
                      selected ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground"
                    }`}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      ))}

      <div className="space-y-2">
        <label className={labelClass}>Row limit</label>
        <input
          type="number"
          className={inputClass}
          value={limit}
          min={1}
          max={10000}
          onChange={(e) => onChange({ source, filters, limit: Number(e.target.value) || 1000 })}
        />
      </div>
    </div>
  );
}

function DeliveryRecipientsField({
  recipients,
  recipientInput,
  scheduleEnabled,
  suggestions,
  onRecipientsChange,
  onInputChange,
}: {
  recipients: string[];
  recipientInput: string;
  scheduleEnabled: boolean;
  suggestions: { email: string; name: string; role: string }[];
  onRecipientsChange: (next: string[]) => void;
  onInputChange: (value: string) => void;
}) {
  return (
    <div className="space-y-2 sm:col-span-2">
      <label className={labelClass}>Deliver to</label>
      <textarea
        className="min-h-[72px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none disabled:opacity-50"
        value={recipientInput}
        onChange={(e) => {
          onInputChange(e.target.value);
          onRecipientsChange(parseRecipientInput(e.target.value));
        }}
        disabled={!scheduleEnabled}
        placeholder="admin@acme.com, security@acme.com"
      />
      <p className="text-xs text-muted-foreground">
        Comma-separated email addresses. Required when scheduled delivery is enabled.
      </p>
      {recipients.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {recipients.map((email) => (
            <Badge key={email} variant="secondary" className="gap-1 font-normal">
              {email}
              {scheduleEnabled && (
                <button
                  type="button"
                  className="ml-1 text-muted-foreground hover:text-foreground"
                  onClick={() => {
                    const next = recipients.filter((item) => item !== email);
                    onRecipientsChange(next);
                    onInputChange(formatRecipientInput(next));
                  }}
                >
                  ×
                </button>
              )}
            </Badge>
          ))}
        </div>
      )}
      {scheduleEnabled && suggestions.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Quick add from tenant users</p>
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((user) => {
              const selected = recipients.some((item) => item.toLowerCase() === user.email.toLowerCase());
              return (
                <button
                  key={user.email}
                  type="button"
                  onClick={() => {
                    const next = toggleRecipient(recipients, user.email);
                    onRecipientsChange(next);
                    onInputChange(formatRecipientInput(next));
                  }}
                  className={`rounded-md border px-2.5 py-1 text-xs ${
                    selected ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground"
                  }`}
                >
                  {user.name} ({user.role.replace("_", " ")})
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export function ReportManagementModals({
  mode,
  report,
  templates,
  token,
  canEdit,
  onClose,
  onSaved,
}: ReportManagementModalsProps) {
  const currentUser = useAuthStore((s) => s.user);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ columns: string[]; rows: unknown[][]; row_count: number } | null>(null);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("Custom");
  const [format, setFormat] = useState("CSV");
  const [query, setQuery] = useState<ApiReportQuery>(
    mode === "query" && report?.query
      ? report.query
      : { source: "audit_logs", filters: { days_back: 30 }, limit: 1000 }
  );

  const [scheduleEnabled, setScheduleEnabled] = useState(
    mode === "schedule" ? (report?.schedule?.enabled ?? false) : false
  );
  const [frequency, setFrequency] = useState(
    mode === "schedule" ? (report?.schedule?.frequency ?? "monthly") : "on_demand"
  );
  const [scheduleTime, setScheduleTime] = useState(
    mode === "schedule" ? (report?.schedule?.time ?? "09:00") : "09:00"
  );
  const [dayOfWeek, setDayOfWeek] = useState(
    mode === "schedule" ? (report?.schedule?.day_of_week ?? 0) : 0
  );
  const [dayOfMonth, setDayOfMonth] = useState(
    mode === "schedule" ? (report?.schedule?.day_of_month ?? 1) : 1
  );
  const [recipients, setRecipients] = useState<string[]>(() => {
    if (mode === "schedule") {
      const saved = report?.schedule?.recipients;
      if (saved?.length) return saved;
    }
    return currentUser?.email ? [currentUser.email] : [];
  });
  const [recipientInput, setRecipientInput] = useState(() => {
    if (mode === "schedule") {
      const saved = report?.schedule?.recipients;
      if (saved?.length) return formatRecipientInput(saved);
    }
    return currentUser?.email ?? "";
  });

  const { data: deliverySuggestions = [] } = useQuery({
    queryKey: ["report-delivery-recipients", token],
    queryFn: async () => {
      if (!token) return [];
      return (await api.getReportDeliveryRecipients(token)).recipients;
    },
    enabled: !!token && (mode === "schedule" || mode === "create"),
    staleTime: 120_000,
  });

  const { data: modalTemplates, isFetching: modalTemplatesLoading } = useQuery({
    queryKey: ["report-query-templates", token],
    queryFn: async () => {
      if (!token) return [];
      const data = await api.getReportQueryTemplates(token);
      return data.templates;
    },
    enabled: !!token && (mode === "query" || mode === "create"),
    staleTime: 300_000,
  });

  const queryTemplates = resolveReportQueryTemplates(modalTemplates ?? templates);
  const templatesLoading = modalTemplatesLoading && queryTemplates.length === 0;

  const scheduledFrequencies = FREQUENCIES.filter((f) => f.value !== "on_demand");

  const schedulePayload = useMemo(
    () => ({
      enabled: scheduleEnabled,
      frequency: scheduleEnabled && frequency === "on_demand" ? "monthly" : frequency,
      time: scheduleTime,
      day_of_week: frequency === "weekly" ? dayOfWeek : null,
      day_of_month: frequency === "monthly" || frequency === "quarterly" ? dayOfMonth : null,
      recipients,
    }),
    [scheduleEnabled, frequency, scheduleTime, dayOfWeek, dayOfMonth, recipients]
  );

  async function handlePreview() {
    if (!token) return;
    setPreviewing(true);
    setError(null);
    try {
      const result = await api.previewReportQuery(token, query);
      setPreview(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Preview failed");
    } finally {
      setPreviewing(false);
    }
  }

  async function handleSaveQuery() {
    if (!token || !report) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateReport(token, report.id, { query });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save query");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveSchedule() {
    if (!token || !report) return;
    if (scheduleEnabled && recipients.length === 0) {
      setError("Add at least one delivery recipient.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.updateReport(token, report.id, { schedule: schedulePayload });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save schedule");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreate() {
    if (!token || !name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.createReport(token, {
        name: name.trim(),
        description: description.trim(),
        category: category.trim() || "Custom",
        format,
        query,
        schedule: scheduleEnabled ? schedulePayload : undefined,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create report");
    } finally {
      setSaving(false);
    }
  }

  if (!mode || !canEdit) return null;

  if (mode === "create") {
    return (
      <ModalShell title="Build New Report" description="Define data source, filters, and optional schedule." onClose={onClose}>
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2 sm:col-span-2">
              <label className={labelClass}>Report name</label>
              <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} placeholder="Weekly Security Summary" />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <label className={labelClass}>Description</label>
              <input className={inputClass} value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className={labelClass}>Category</label>
              <input className={inputClass} value={category} onChange={(e) => setCategory(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className={labelClass}>Export format</label>
              <select className={inputClass} value={format} onChange={(e) => setFormat(e.target.value)}>
                <option value="CSV">CSV</option>
                <option value="PDF">PDF</option>
              </select>
            </div>
          </div>

          <QueryBuilder
            source={query.source}
            filters={query.filters}
            limit={query.limit}
            templates={queryTemplates}
            templatesLoading={templatesLoading}
            onChange={setQuery}
          />

          <div className="rounded-md border border-border/60 p-4">
            <label className="flex items-center gap-2 text-sm font-medium">
              <input type="checkbox" checked={scheduleEnabled} onChange={(e) => setScheduleEnabled(e.target.checked)} />
              Schedule on create
            </label>
            {scheduleEnabled && (
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <select className={inputClass} value={frequency === "on_demand" ? "monthly" : frequency} onChange={(e) => setFrequency(e.target.value)}>
                  {scheduledFrequencies.map((f) => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                  ))}
                </select>
                <input type="time" className={inputClass} value={scheduleTime} onChange={(e) => setScheduleTime(e.target.value)} />
                <DeliveryRecipientsField
                  recipients={recipients}
                  recipientInput={recipientInput}
                  scheduleEnabled={scheduleEnabled}
                  suggestions={deliverySuggestions}
                  onRecipientsChange={setRecipients}
                  onInputChange={setRecipientInput}
                />
              </div>
            )}
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleCreate} disabled={saving || !name.trim()} className="gap-2">
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              Create Report
            </Button>
          </div>
        </div>
      </ModalShell>
    );
  }

  if (mode === "query" && report) {
    return (
      <ModalShell title="Edit Report Query" description={report.name} onClose={onClose}>
        <QueryBuilder
          source={query.source}
          filters={query.filters}
          limit={query.limit}
          templates={queryTemplates}
          templatesLoading={templatesLoading}
          onChange={setQuery}
        />

        {preview && (
          <div className="mt-4 rounded-md border border-border/60 p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium">Preview</p>
              <Badge variant="outline">{preview.row_count} rows</Badge>
            </div>
            <div className="max-h-40 overflow-auto text-xs font-mono text-muted-foreground">
              {preview.rows.slice(0, 5).map((row, i) => (
                <div key={i} className="border-b border-border/40 py-1 last:border-0">{JSON.stringify(row)}</div>
              ))}
            </div>
          </div>
        )}

        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button variant="outline" onClick={handlePreview} disabled={previewing} className="gap-2">
            {previewing && <Loader2 className="h-4 w-4 animate-spin" />}
            Preview Query
          </Button>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSaveQuery} disabled={saving} className="gap-2">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Save Query
          </Button>
        </div>
      </ModalShell>
    );
  }

  if (mode === "schedule" && report) {
    return (
      <ModalShell title="Schedule Report" description={report.name} onClose={onClose}>
        <div className="space-y-4">
          <label className="flex items-center gap-2 text-sm font-medium">
            <input
              type="checkbox"
              checked={scheduleEnabled}
              onChange={(e) => {
                const enabled = e.target.checked;
                setScheduleEnabled(enabled);
                if (enabled && frequency === "on_demand") {
                  setFrequency("monthly");
                }
              }}
            />
            Enable scheduled delivery
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className={labelClass}>Frequency</label>
              <select
                className={inputClass}
                value={scheduleEnabled && frequency === "on_demand" ? "monthly" : frequency}
                onChange={(e) => setFrequency(e.target.value)}
                disabled={!scheduleEnabled}
              >
                {(scheduleEnabled ? scheduledFrequencies : FREQUENCIES).map((f) => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className={labelClass}>Time (UTC)</label>
              <input
                type="time"
                className={inputClass}
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
                disabled={!scheduleEnabled || frequency === "on_demand"}
              />
            </div>
            <DeliveryRecipientsField
              recipients={recipients}
              recipientInput={recipientInput}
              scheduleEnabled={scheduleEnabled}
              suggestions={deliverySuggestions}
              onRecipientsChange={setRecipients}
              onInputChange={setRecipientInput}
            />
            {frequency === "weekly" && scheduleEnabled && (
              <div className="space-y-2 sm:col-span-2">
                <label className={labelClass}>Day of week</label>
                <select className={inputClass} value={dayOfWeek} onChange={(e) => setDayOfWeek(Number(e.target.value))}>
                  {DAYS.map((day, i) => (
                    <option key={day} value={i}>{day}</option>
                  ))}
                </select>
              </div>
            )}
            {(frequency === "monthly" || frequency === "quarterly") && scheduleEnabled && (
              <div className="space-y-2 sm:col-span-2">
                <label className={labelClass}>Day of month</label>
                <input
                  type="number"
                  min={1}
                  max={28}
                  className={inputClass}
                  value={dayOfMonth}
                  onChange={(e) => setDayOfMonth(Number(e.target.value))}
                />
              </div>
            )}
          </div>

          {report.schedule?.next_run_at && scheduleEnabled && frequency !== "on_demand" && (
            <p className="text-xs text-muted-foreground">
              Next run: {new Date(report.schedule.next_run_at).toLocaleString()}
              {recipients.length > 0 && ` · Delivering to ${recipients.length} recipient${recipients.length === 1 ? "" : "s"}`}
            </p>
          )}

          {error && <p className="text-sm text-red-400">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleSaveSchedule} disabled={saving} className="gap-2">
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              Save Schedule
            </Button>
          </div>
        </div>
      </ModalShell>
    );
  }

  return null;
}
