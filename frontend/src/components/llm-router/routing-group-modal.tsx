"use client";

import { useEffect, useState } from "react";
import { Loader2, Plus, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  api,
  type ApiRoutingGroup,
  type ApiRoutingGroupCreateRequest,
  type ApiRoutingGroupMember,
  type ApiRoutingGroupUpdateRequest,
} from "@/lib/api";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50";
const labelClass = "text-sm font-medium";

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
        className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl"
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

interface RoutingGroupModalProps {
  open: boolean;
  group: ApiRoutingGroup | null;
  token: string | null;
  onClose: () => void;
  onSaved: () => void;
}

export function RoutingGroupModal({
  open,
  group,
  token,
  onClose,
  onSaved,
}: RoutingGroupModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [strategy, setStrategy] = useState("weighted");
  const [status, setStatus] = useState("active");
  const [members, setMembers] = useState<ApiRoutingGroupMember[]>([
    { model: "gpt-4o", weight: 70, priority: 1 },
    { model: "gemini-1.5-pro", weight: 30, priority: 2 },
  ]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = Boolean(group);

  useEffect(() => {
    if (group) {
      setName(group.name || "");
      setDescription(group.description || "");
      setStrategy(group.strategy || "weighted");
      setStatus(group.status || "active");
      setMembers(
        group.members && group.members.length > 0
          ? group.members
          : [{ model: "gpt-4o", weight: 100, priority: 1 }]
      );
    } else {
      setName("");
      setDescription("");
      setStrategy("weighted");
      setStatus("active");
      setMembers([
        { model: "gpt-4o", weight: 70, priority: 1 },
        { model: "gemini-1.5-pro", weight: 30, priority: 2 },
      ]);
    }
    setError(null);
  }, [group, open]);

  if (!open) return null;

  function addMember() {
    setMembers((prev) => [
      ...prev,
      { model: "", weight: 0, priority: prev.length + 1 },
    ]);
  }

  function removeMember(index: number) {
    setMembers((prev) => prev.filter((_, idx) => idx !== index));
  }

  function updateMember(index: number, field: keyof ApiRoutingGroupMember, val: string | number) {
    setMembers((prev) =>
      prev.map((m, idx) => (idx === index ? { ...m, [field]: val } : m))
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    if (!name.trim()) {
      setError("Routing group name is required.");
      return;
    }
    if (members.length === 0) {
      setError("At least one target model member is required.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      if (isEdit && group) {
        const body: ApiRoutingGroupUpdateRequest = {
          name: name.trim(),
          description: description.trim(),
          strategy,
          status,
          members,
        };
        await api.updateRoutingGroup(token, group.id, body);
      } else {
        const body: ApiRoutingGroupCreateRequest = {
          name: name.trim(),
          description: description.trim(),
          strategy,
          status,
          members,
        };
        await api.createRoutingGroup(token, body);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save routing group");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell
      title={isEdit ? "Edit Routing Group" : "Create Routing Group"}
      description="Define a virtual model group alias with weighted distribution or priority failover."
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <div>
          <label className={labelClass}>Group Alias Name</label>
          <input
            type="text"
            className={inputClass}
            placeholder="e.g. production, fast-models, gpt4-fallback"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Clients can use this alias directly in <code className="text-[11px]">model: &quot;{name || "alias"}&quot;</code> API requests.
          </p>
        </div>

        <div>
          <label className={labelClass}>Description</label>
          <input
            type="text"
            className={inputClass}
            placeholder="e.g. Primary production model pool with failover"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>Routing Strategy</label>
            <select
              className={inputClass}
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
            >
              <option value="weighted">Weighted Ratio (%)</option>
              <option value="failover">Priority Failover Rank</option>
            </select>
          </div>

          <div>
            <label className={labelClass}>Status</label>
            <select
              className={inputClass}
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className={labelClass}>Member Target Models</label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={addMember}
            >
              <Plus className="mr-1 h-3 w-3" /> Add Model
            </Button>
          </div>

          <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
            {members.map((member, idx) => (
              <div key={idx} className="flex items-center gap-2 rounded-md border border-border p-2 bg-background/50">
                <div className="flex-1">
                  <input
                    type="text"
                    className="h-8 w-full rounded border border-input px-2 text-xs"
                    placeholder="Provider / Model (e.g. gpt-4o)"
                    value={member.model}
                    onChange={(e) => updateMember(idx, "model", e.target.value)}
                  />
                </div>
                {strategy === "weighted" ? (
                  <div className="w-24">
                    <div className="flex items-center text-xs">
                      <input
                        type="number"
                        className="h-8 w-16 rounded border border-input px-2 text-xs"
                        value={member.weight}
                        min={0}
                        max={100}
                        onChange={(e) => updateMember(idx, "weight", parseFloat(e.target.value) || 0)}
                      />
                      <span className="ml-1 text-muted-foreground">%</span>
                    </div>
                  </div>
                ) : (
                  <div className="w-24">
                    <div className="flex items-center text-xs">
                      <span className="mr-1 text-muted-foreground">Rank</span>
                      <input
                        type="number"
                        className="h-8 w-14 rounded border border-input px-2 text-xs"
                        value={member.priority}
                        min={1}
                        onChange={(e) => updateMember(idx, "priority", parseInt(e.target.value, 10) || 1)}
                      />
                    </div>
                  </div>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                  onClick={() => removeMember(idx)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isEdit ? "Save Changes" : "Create Group"}
          </Button>
        </div>
      </form>
    </ModalShell>
  );
}
