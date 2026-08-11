"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Loader2, Plus, X } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiTenantUser } from "@/lib/api";
import { useAuthStore, type UserRole } from "@/stores/auth-store";

const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: "tenant_admin", label: "Tenant Admin" },
  { value: "security_admin", label: "Security Admin" },
  { value: "compliance_officer", label: "Compliance Officer" },
  { value: "auditor", label: "Auditor" },
  { value: "developer", label: "Developer" },
];

const PERMISSION_LABELS: Record<string, string> = {
  manage_tenants: "Manage tenants",
  manage_users: "Manage users",
  manage_policies: "Manage policies",
  view_audit_logs: "View audit logs",
  manage_mcp: "Manage MCP servers",
  use_studio: "Use Governance Sandbox",
  view_compliance: "View compliance",
  manage_llm_providers: "Manage LLM providers",
};

const ROLE_LABELS: Record<string, string> = {
  platform_admin: "Platform Admin",
  tenant_admin: "Tenant Admin",
  security_admin: "Security Admin",
  compliance_officer: "Compliance Officer",
  auditor: "Auditor",
  developer: "Developer",
};

export function RbacSettings() {
  const token = useAuthStore((s) => s.token);
  const currentUser = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [pendingUserId, setPendingUserId] = useState<string | null>(null);
  const [newUserName, setNewUserName] = useState("");
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [newUserRole, setNewUserRole] = useState<UserRole>("developer");
  const [showAddUser, setShowAddUser] = useState(false);

  const { data: permissionsData } = useQuery({
    queryKey: ["rbac-permissions", token],
    queryFn: () => api.getRbacPermissions(token!),
    enabled: Boolean(token),
  });

  const { data: matrixData } = useQuery({
    queryKey: ["rbac-matrix", token],
    queryFn: () => api.getRbacMatrix(token!),
    enabled: Boolean(token),
  });

  const canManageUsers = permissionsData?.permissions.includes("manage_users") ?? false;

  const { data: users = [], isLoading: usersLoading } = useQuery({
    queryKey: ["tenant-users", token],
    queryFn: () => api.listUsers(token!),
    enabled: Boolean(token) && canManageUsers,
  });

  const updateUser = useMutation({
    mutationFn: ({ userId, role, is_active }: { userId: string; role?: string; is_active?: boolean }) =>
      api.updateUser(token!, userId, { role, is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-users"] });
      setPendingUserId(null);
    },
  });

  const createUser = useMutation({
    mutationFn: () =>
      api.createUser(token!, {
        name: newUserName.trim(),
        email: newUserEmail.trim(),
        password: newUserPassword,
        role: newUserRole,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-users"] });
      setNewUserName("");
      setNewUserEmail("");
      setNewUserPassword("");
      setNewUserRole("developer");
      setShowAddUser(false);
    },
  });

  const matrixRows = useMemo(() => {
    if (!matrixData) return [];
    return matrixData.permissions.map((permission) => ({
      permission,
      label: PERMISSION_LABELS[permission] ?? permission,
      cells: matrixData.roles.map((role) => matrixData.matrix[role]?.[permission] ?? false),
    }));
  }, [matrixData]);

  function handleRoleChange(user: ApiTenantUser, role: string) {
    if (role === user.role) return;
    setPendingUserId(user.id);
    updateUser.mutate({ userId: user.id, role });
  }

  function handleToggleActive(user: ApiTenantUser) {
    setPendingUserId(user.id);
    updateUser.mutate({ userId: user.id, is_active: !user.is_active });
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle>Role-Based Access Control</CardTitle>
        <CardDescription>
          {canManageUsers
            ? "Add or deactivate users, change roles, and review the permission matrix"
            : "Your role permissions and the tenant permission matrix (read-only)"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {permissionsData && (
          <div className="rounded-lg border border-border/60 p-4">
            <p className="text-sm text-muted-foreground">Your permissions</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {permissionsData.permissions.length === 0 ? (
                <span className="text-sm text-muted-foreground">No elevated permissions</span>
              ) : (
                permissionsData.permissions.map((perm) => (
                  <Badge key={perm} variant="secondary">
                    {PERMISSION_LABELS[perm] ?? perm}
                  </Badge>
                ))
              )}
            </div>
          </div>
        )}

        {canManageUsers && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-medium">Tenant users</h3>
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setShowAddUser((v) => !v)}>
                <Plus className="h-3.5 w-3.5" />
                Add user
              </Button>
            </div>

            {showAddUser && (
              <div className="space-y-3 rounded-lg border border-dashed border-border/60 p-4">
                <p className="text-sm font-medium">New tenant user</p>
                <input
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                  placeholder="Full name"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                />
                <input
                  type="email"
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  placeholder="Email"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                />
                <input
                  type="password"
                  value={newUserPassword}
                  onChange={(e) => setNewUserPassword(e.target.value)}
                  placeholder="Temporary password (min 8 characters)"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                />
                <select
                  value={newUserRole}
                  onChange={(e) => setNewUserRole(e.target.value as UserRole)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {ROLE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {createUser.isError && (
                  <p className="text-xs text-destructive">
                    {createUser.error instanceof Error ? createUser.error.message : "Failed to create user"}
                  </p>
                )}
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    disabled={
                      !newUserName.trim() ||
                      !newUserEmail.trim() ||
                      newUserPassword.length < 8 ||
                      createUser.isPending
                    }
                    onClick={() => createUser.mutate()}
                  >
                    {createUser.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create user"}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setShowAddUser(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {usersLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading users…
              </div>
            ) : (
              <div className="space-y-2">
                {users.map((user) => (
                  <div
                    key={user.id}
                    className="flex flex-col gap-3 rounded-lg border border-border/60 p-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="font-medium">{user.name}</p>
                      <p className="truncate text-sm text-muted-foreground">{user.email}</p>
                      {!user.is_active && (
                        <Badge variant="outline" className="mt-1">
                          Inactive
                        </Badge>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <select
                        value={user.role}
                        disabled={updateUser.isPending && pendingUserId === user.id}
                        onChange={(e) => handleRoleChange(user, e.target.value)}
                        className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                      >
                        {ROLE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      {user.id !== currentUser?.id && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={updateUser.isPending && pendingUserId === user.id}
                          onClick={() => handleToggleActive(user)}
                        >
                          {user.is_active ? "Deactivate" : "Activate"}
                        </Button>
                      )}
                      {user.id === currentUser?.id && <Badge>You</Badge>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {matrixData && (
          <div className="space-y-3">
            <h3 className="text-sm font-medium">Permission matrix</h3>
            <div className="overflow-x-auto rounded-lg border border-border/60">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="border-b border-border/60 bg-muted/30">
                    <th className="px-3 py-2 text-left font-medium">Permission</th>
                    {matrixData.roles.map((role) => (
                      <th key={role} className="px-3 py-2 text-center font-medium">
                        {ROLE_LABELS[role] ?? role}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {matrixRows.map((row) => (
                    <tr key={row.permission} className="border-b border-border/40 last:border-0">
                      <td className="px-3 py-2">{row.label}</td>
                      {row.cells.map((allowed, index) => (
                        <td key={`${row.permission}-${matrixData.roles[index]}`} className="px-3 py-2 text-center">
                          {allowed ? (
                            <Check className="mx-auto h-4 w-4 text-emerald-500" />
                          ) : (
                            <X className="mx-auto h-4 w-4 text-muted-foreground/40" />
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
