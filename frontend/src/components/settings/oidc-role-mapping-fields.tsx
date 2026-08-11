"use client";

import { useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export const OIDC_ROLE_OPTIONS = [
  { value: "tenant_admin", label: "Tenant Admin" },
  { value: "security_admin", label: "Security Admin" },
  { value: "compliance_officer", label: "Compliance Officer" },
  { value: "auditor", label: "Auditor" },
  { value: "developer", label: "Developer" },
] as const;

export type OidcRoleMapping = Record<string, string>;

interface OidcRoleMappingFieldsProps {
  roleClaim: string;
  roleMapping: OidcRoleMapping;
  onRoleClaimChange: (value: string) => void;
  onRoleMappingChange: (mapping: OidcRoleMapping) => void;
  disabled?: boolean;
}

function mappingRows(mapping: OidcRoleMapping): { id: string; group: string; role: string }[] {
  const entries = Object.entries(mapping);
  if (entries.length === 0) {
    return [];
  }
  return entries.map(([group, role], index) => ({
    id: `row-${index}-${group}`,
    group,
    role,
  }));
}

export function OidcRoleMappingFields({
  roleClaim,
  roleMapping,
  onRoleClaimChange,
  onRoleMappingChange,
  disabled,
}: OidcRoleMappingFieldsProps) {
  const [blankRowCount, setBlankRowCount] = useState(0);

  const rows = useMemo(() => {
    const mapped = mappingRows(roleMapping);
    const blanks = Array.from({ length: blankRowCount }, (_, index) => ({
      id: `blank-${index}`,
      group: "",
      role: "developer",
    }));
    if (mapped.length === 0 && blanks.length === 0) {
      return [{ id: "default-blank", group: "", role: "developer" }];
    }
    return [...mapped, ...blanks];
  }, [roleMapping, blankRowCount]);

  function commitRows(nextRows: { group: string; role: string }[]) {
    const nextMapping: OidcRoleMapping = {};
    for (const row of nextRows) {
      const group = row.group.trim();
      if (group) {
        nextMapping[group] = row.role;
      }
    }
    onRoleMappingChange(nextMapping);
  }

  function updateRow(index: number, patch: Partial<{ group: string; role: string }>) {
    const nextRows = rows.map((row, i) => (i === index ? { ...row, ...patch } : row));
    commitRows(nextRows);
    if (patch.group !== undefined) {
      setBlankRowCount(0);
    }
  }

  function addRow() {
    if (rows.every((row) => row.group.trim())) {
      setBlankRowCount((count) => count + 1);
    }
  }

  function removeRow(index: number) {
    const nextRows = rows.filter((_, i) => i !== index);
    commitRows(nextRows);
    setBlankRowCount(Math.max(0, blankRowCount - 1));
  }

  return (
    <div className="space-y-3 rounded-md border border-border/60 bg-muted/10 p-3">
      <div>
        <label className="text-xs font-medium text-muted-foreground">IdP groups claim</label>
        <input
          value={roleClaim}
          disabled={disabled}
          onChange={(e) => onRoleClaimChange(e.target.value)}
          placeholder="groups"
          className="mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
        />
        <p className="mt-1 text-xs text-muted-foreground">
          JWT claim that lists IdP groups (e.g. <code className="rounded bg-muted px-1">groups</code> for Okta,
          Azure AD app roles).
        </p>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-xs font-medium text-muted-foreground">Group → PySetu role</span>
          <Button type="button" variant="ghost" size="sm" className="h-7 gap-1 px-2" disabled={disabled} onClick={addRow}>
            <Plus className="h-3.5 w-3.5" />
            Add rule
          </Button>
        </div>
        <div className="space-y-2">
          {rows.map((row, index) => (
            <div key={row.id} className="flex flex-wrap items-center gap-2">
              <input
                value={row.group}
                disabled={disabled}
                onChange={(e) => updateRow(index, { group: e.target.value })}
                placeholder="IdP group name"
                className="min-w-[140px] flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              />
              <span className="text-xs text-muted-foreground">→</span>
              <select
                value={row.role}
                disabled={disabled}
                onChange={(e) => updateRow(index, { role: e.target.value })}
                className="h-9 rounded-md border border-input bg-background px-2 text-sm"
              >
                {OIDC_ROLE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                disabled={disabled || rows.length <= 1}
                onClick={() => removeRow(index)}
              >
                <Trash2 className="h-4 w-4 text-red-400" />
              </Button>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          First matching group in the user&apos;s claim wins. Unmapped SSO users receive the platform default role (
          <code className="rounded bg-muted px-1">developer</code> unless changed in backend config).
        </p>
      </div>
    </div>
  );
}

export function formatRoleMappingSummary(mapping: OidcRoleMapping): string {
  const entries = Object.entries(mapping);
  if (entries.length === 0) return "No group rules — default role applies";
  return entries.map(([group, role]) => `${group} → ${role}`).join(", ");
}
