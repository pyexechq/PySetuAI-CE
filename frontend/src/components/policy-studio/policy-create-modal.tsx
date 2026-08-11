"use client";

import { useMemo, useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import type { PolicyTreeNode } from "@/lib/mock-data";

interface PolicyCreateModalProps {
  open: boolean;
  tree: PolicyTreeNode[];
  token: string | null;
  canEdit: boolean;
  onClose: () => void;
  onCreated: (node: PolicyTreeNode, parentId: string | null) => void;
}

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

function collectFolderOptions(nodes: PolicyTreeNode[], depth = 0): { id: string; label: string }[] {
  const options: { id: string; label: string }[] = [];
  for (const node of nodes) {
    if (node.type === "folder") {
      options.push({ id: node.id, label: `${"\u00A0".repeat(depth * 2)}${node.label}` });
      if (node.children?.length) {
        options.push(...collectFolderOptions(node.children, depth + 1));
      }
    }
  }
  return options;
}

function insertIntoTree(
  nodes: PolicyTreeNode[],
  parentId: string | null,
  newNode: PolicyTreeNode
): PolicyTreeNode[] {
  if (!parentId) {
    return [...nodes, newNode];
  }
  return nodes.map((node) => {
    if (node.id === parentId) {
      return { ...node, children: [...(node.children ?? []), newNode] };
    }
    if (node.children?.length) {
      return { ...node, children: insertIntoTree(node.children, parentId, newNode) };
    }
    return node;
  });
}

export function insertPolicyNode(
  tree: PolicyTreeNode[],
  node: PolicyTreeNode,
  parentId: string | null
): PolicyTreeNode[] {
  return insertIntoTree(tree, parentId, node);
}

export function PolicyCreateModal({
  open,
  tree,
  token,
  canEdit,
  onClose,
  onCreated,
}: PolicyCreateModalProps) {
  const folderOptions = useMemo(() => collectFolderOptions(tree), [tree]);

  const [name, setName] = useState("");
  const [policyType, setPolicyType] = useState<"policy" | "folder">("policy");
  const [status, setStatus] = useState<"active" | "draft" | "disabled">("draft");
  const [parentId, setParentId] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function handleCreate() {
    if (!name.trim()) return;

    setSaving(true);
    setError(null);

    const parent = parentId || null;

    try {
      if (token && canEdit) {
        const created = await api.createPolicy(token, {
          name: name.trim(),
          policy_type: policyType,
          status: policyType === "policy" ? status : undefined,
          parent_id: parent,
        });
        onCreated(
          {
            id: created.id,
            label: created.label,
            type: created.type as PolicyTreeNode["type"],
            status: created.status as PolicyTreeNode["status"],
          },
          parent
        );
      } else {
        const localNode: PolicyTreeNode = {
          id: `${policyType}-${Date.now()}`,
          label: name.trim(),
          type: policyType,
          status: policyType === "policy" ? status : undefined,
        };
        onCreated(localNode, parent);
      }

      setName("");
      setPolicyType("policy");
      setStatus("draft");
      setParentId("");
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create policy");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell
      title="Create Policy"
      description="Add a new policy or folder to the policy tree."
      onClose={onClose}
    >
      <div className="space-y-4">
        {!canEdit && token && (
          <p className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
            Admin access is required to persist new policies. Changes will apply locally only.
          </p>
        )}

        <div className="space-y-2">
          <label className={labelClass} htmlFor="policy-name">
            Name
          </label>
          <input
            id="policy-name"
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Custom Data Filter"
            autoFocus
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className={labelClass} htmlFor="policy-type">
              Type
            </label>
            <select
              id="policy-type"
              className={inputClass}
              value={policyType}
              onChange={(e) => setPolicyType(e.target.value as "policy" | "folder")}
            >
              <option value="policy">Policy</option>
              <option value="folder">Folder</option>
            </select>
          </div>

          {policyType === "policy" && (
            <div className="space-y-2">
              <label className={labelClass} htmlFor="policy-status">
                Status
              </label>
              <select
                id="policy-status"
                className={inputClass}
                value={status}
                onChange={(e) => setStatus(e.target.value as "active" | "draft" | "disabled")}
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>
          )}
        </div>

        <div className="space-y-2">
          <label className={labelClass} htmlFor="policy-parent">
            Parent folder
          </label>
          <select
            id="policy-parent"
            className={inputClass}
            value={parentId}
            onChange={(e) => setParentId(e.target.value)}
          >
            <option value="">Root level</option>
            {folderOptions.map((folder) => (
              <option key={folder.id} value={folder.id}>
                {folder.label}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={saving || !name.trim()} className="gap-2">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Create
          </Button>
        </div>
      </div>
    </ModalShell>
  );
}
