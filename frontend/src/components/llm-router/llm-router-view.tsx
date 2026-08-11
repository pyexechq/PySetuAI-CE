"use client";

import { useMemo, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LlmProviderModal } from "@/components/llm-router/llm-provider-modal";
import { RoutingRuleModal } from "@/components/llm-router/routing-rule-modal";
import { useLlmRouting } from "@/hooks/use-llm-routing";
import { api, ApiError, type ApiRoutingModel, type ApiRoutingRule } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

export function LlmRouterView() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const canEdit = user?.role === "tenant_admin" || user?.role === "security_admin";
  const { models, rules, invalidateProviders, invalidateRules } = useLlmRouting();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ApiRoutingModel | null>(null);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ApiRoutingRule | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [rebalancing, setRebalancing] = useState(false);

  const activeModels = useMemo(() => models.filter((m) => m.isActive !== false), [models]);
  const totalRequests = activeModels.reduce((sum, m) => sum + m.requests, 0);

  function openCreateModal() {
    setEditingProvider(null);
    setModalOpen(true);
  }

  function openEditModal(model: (typeof models)[0]) {
    if (!model.id) return;
    setEditingProvider({
      id: model.id,
      model: model.model,
      provider_type: model.providerType ?? "custom",
      requests: model.requests,
      percentage: model.percentage,
      latency: model.latency,
      success_rate: model.successRate,
      is_active: model.isActive !== false,
      api_key_set: model.apiKeySet,
      api_key_masked: model.apiKeyMasked,
    });
    setModalOpen(true);
  }

  async function deactivateProvider(model: (typeof models)[0]) {
    if (!token || !model.id) return;
    if (!window.confirm(`Deactivate ${model.model}? It will be removed from active routing.`)) return;

    setActionError(null);
    try {
      await api.deleteLlmProvider(token, model.id);
      invalidateProviders();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to deactivate provider");
    }
  }

  function openCreateRuleModal() {
    setEditingRule(null);
    setRuleModalOpen(true);
  }

  function openEditRuleModal(rule: (typeof rules)[0]) {
    setEditingRule({
      id: rule.id,
      name: rule.name,
      priority: rule.priority,
      condition: rule.condition,
      target_model: rule.targetModel,
      status: rule.status,
    });
    setRuleModalOpen(true);
  }

  async function deleteRule(rule: (typeof rules)[0]) {
    if (!token) return;
    if (!window.confirm(`Delete routing rule "${rule.name}"?`)) return;

    setActionError(null);
    try {
      await api.deleteRoutingRule(token, rule.id);
      invalidateRules();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to delete routing rule");
    }
  }

  async function rebalanceFromTraffic() {
    if (!token) return;
    setActionError(null);
    setRebalancing(true);
    try {
      await api.rebalanceLlmProviders(token);
      invalidateProviders();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to rebalance routing shares");
    } finally {
      setRebalancing(false);
    }
  }

  const targetModelOptions = activeModels.map((m) => m.model);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Total Routed</p>
            <p className="text-2xl font-bold">{formatNumber(totalRequests)}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Active Rules</p>
            <p className="text-2xl font-bold">{rules.filter((r) => r.status === "active").length}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Registered Providers</p>
            <p className="text-2xl font-bold">{activeModels.length}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle>Routing Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={activeModels}
                  dataKey="requests"
                  nameKey="model"
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                >
                  {activeModels.map((entry) => (
                    <Cell key={entry.model} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                  formatter={(value) => formatNumber(Number(value))}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-2 text-center">
              <p className="text-2xl font-bold">{formatNumber(totalRequests)}</p>
              <p className="text-xs text-muted-foreground">Total requests routed</p>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2 border-border/60 bg-card/50">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
            <CardTitle>Model Performance</CardTitle>
            {canEdit && (
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5"
                  disabled={rebalancing || totalRequests === 0}
                  onClick={rebalanceFromTraffic}
                >
                  <RefreshCw className={`h-4 w-4 ${rebalancing ? "animate-spin" : ""}`} />
                  {rebalancing ? "Rebalancing…" : "Rebalance from traffic"}
                </Button>
                <Button size="sm" className="gap-1.5" onClick={openCreateModal}>
                  <Plus className="h-4 w-4" />
                  Register provider
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent>
            {actionError && <p className="mb-3 text-sm text-red-400">{actionError}</p>}
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-3 font-medium">Model</th>
                  <th className="pb-3 font-medium">Type</th>
                  <th className="pb-3 font-medium text-right">Requests</th>
                  <th className="pb-3 font-medium text-right">Share</th>
                  <th className="pb-3 font-medium text-right">Latency</th>
                  <th className="pb-3 font-medium text-right">Success</th>
                  {canEdit && <th className="pb-3 font-medium text-right">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {models.map((row) => (
                  <tr key={row.id ?? row.model} className="border-b border-border/50 last:border-0">
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: row.color }} />
                        <span>{row.model}</span>
                        {row.isActive === false && (
                          <Badge variant="outline" className="text-[10px]">
                            inactive
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="py-3 capitalize text-muted-foreground">{row.providerType ?? "—"}</td>
                    <td className="py-3 text-right">{formatNumber(row.requests)}</td>
                    <td className="py-3 text-right">{row.percentage}%</td>
                    <td className="py-3 text-right">{row.latency}ms</td>
                    <td className="py-3 text-right text-emerald-400">{row.successRate}%</td>
                    {canEdit && (
                      <td className="py-3">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                            disabled={!row.id}
                            onClick={() => openEditModal(row)}
                            aria-label={`Edit ${row.model}`}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-red-400 hover:text-red-300"
                            disabled={!row.id || row.isActive === false}
                            onClick={() => deactivateProvider(row)}
                            aria-label={`Deactivate ${row.model}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            {canEdit && (
              <p className="mt-3 text-xs text-muted-foreground">
                Routing share (%) controls weighted distribution when gateway requests use{" "}
                <code className="text-[11px]">model: auto</code> and no active rule matches. Request counts,
                latency, and success rate update automatically from gateway traffic.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card/50">
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
          <CardTitle>Routing Rules</CardTitle>
          {canEdit && (
            <Button size="sm" className="gap-1.5" onClick={openCreateRuleModal}>
              <Plus className="h-4 w-4" />
              Add rule
            </Button>
          )}
        </CardHeader>
        <CardContent className="p-5 pt-0">
          {actionError && <p className="mb-3 text-sm text-red-400">{actionError}</p>}
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-3 font-medium">Priority</th>
                <th className="pb-3 font-medium">Rule</th>
                <th className="pb-3 font-medium">Condition</th>
                <th className="pb-3 font-medium">Target Model</th>
                <th className="pb-3 font-medium">Status</th>
                {canEdit && <th className="pb-3 font-medium text-right">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {rules.length === 0 ? (
                <tr>
                  <td colSpan={canEdit ? 6 : 5} className="py-8 text-center text-muted-foreground">
                    No routing rules configured. Add a rule to steer traffic by condition.
                  </td>
                </tr>
              ) : (
                rules.map((rule) => (
                <tr key={rule.id} className="border-b border-border/50 last:border-0">
                  <td className="py-3 text-muted-foreground">{rule.priority}</td>
                  <td className="py-3 font-medium">{rule.name}</td>
                  <td className="py-3 font-mono text-xs text-muted-foreground">{rule.condition}</td>
                  <td className="py-3">{rule.targetModel}</td>
                  <td className="py-3">
                    <Badge variant={rule.status === "active" ? "success" : "warning"}>{rule.status}</Badge>
                  </td>
                  {canEdit && (
                    <td className="py-3">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={() => openEditRuleModal(rule)}
                          aria-label={`Edit ${rule.name}`}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 text-red-400 hover:text-red-300"
                          onClick={() => deleteRule(rule)}
                          aria-label={`Delete ${rule.name}`}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  )}
                </tr>
              ))
              )}
            </tbody>
          </table>
          {canEdit && (
            <p className="mt-3 text-xs text-muted-foreground">
              Lower priority runs first. Set status to <strong>active</strong> to enforce in the live router; use{" "}
              <strong>draft</strong> to stage changes.
            </p>
          )}
        </CardContent>
      </Card>

      <LlmProviderModal
        open={modalOpen}
        provider={editingProvider}
        token={token}
        onClose={() => setModalOpen(false)}
        onSaved={invalidateProviders}
      />

      <RoutingRuleModal
        open={ruleModalOpen}
        rule={editingRule}
        targetModels={targetModelOptions}
        token={token}
        onClose={() => setRuleModalOpen(false)}
        onSaved={invalidateRules}
      />
    </div>
  );
}
