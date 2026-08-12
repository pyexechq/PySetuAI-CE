"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronRight, ChevronDown, FileText, Folder, GitBranch, List, Plus, Trash2, Workflow, X, Sparkles, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { PolicyRule, PolicyTreeNode } from "@/lib/types/domain";
import { usePolicyRules, usePolicyTree } from "@/hooks/use-policies";
import { api, ApiError } from "@/lib/api";
import { toast } from "react-hot-toast";
import { usePolicyGraphLinks } from "@/hooks/use-policy-graph-links";
import {
  findFirstPolicy,
  findPolicyInTree,
  graphUrlForPolicy,
  type PolicyGraphLink,
} from "@/lib/policy-graph-map";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PolicyTesterModal } from "./policy-tester-modal";
import { insertPolicyNode, PolicyCreateModal } from "@/components/policy-studio/policy-create-modal";
import { PolicyFlowCanvas } from "@/components/policy-studio/policy-flow-canvas";
import { PolicyAiHelper } from "@/components/policy-studio/policy-ai-helper";
import { CustomIntentsPanel } from "@/components/policy-studio/custom-intents-panel";
import { ComplianceTemplateModal } from "@/components/policy-studio/compliance-template-modal";
import {
  PolicyConditionHelpButton,
  type PolicyConditionHelpExample,
} from "@/components/policy-studio/policy-condition-help";
import { useAuthStore } from "@/stores/auth-store";

type PolicyViewMode = "list" | "flow";

function orderRules(rules: PolicyRule[], order: string[] | undefined): PolicyRule[] {
  if (!order?.length) return rules;
  const byId = new Map(rules.map((r) => [r.id, r]));
  const ordered = order.filter((id) => byId.has(id)).map((id) => byId.get(id)!);
  const remaining = rules.filter((r) => !order.includes(r.id));
  return [...ordered, ...remaining];
}

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2";
const labelClass = "text-sm font-medium";

const RULE_ACTIONS = ["Block", "Redact", "Alert", "Allow"] as const;
const RULE_SEVERITIES = ["low", "medium", "high", "critical"] as const;
const POLICY_STATUSES = ["active", "draft", "disabled"] as const;
const STARTER_POLICY_NAMES = new Set([
  "Prompt Injection Guard",
  "PII Redaction — EU",
  "PII Redaction — US",
  "Jailbreak Prevention",
]);

function createEmptyRule(): PolicyRule {
  return {
    id: `r-${crypto.randomUUID().slice(0, 8)}`,
    name: "",
    condition: "",
    action: "Block",
    severity: "medium",
    enabled: true,
  };
}

function PolicyRuleEditorModal({
  rule,
  mode,
  onClose,
  onSave,
  onDelete,
}: {
  rule: PolicyRule;
  mode: "create" | "edit";
  onClose: () => void;
  onSave: (updated: PolicyRule) => void;
  onDelete?: () => void;
}) {
  const [draft, setDraft] = useState<PolicyRule>(rule);

  function handleSave() {
    if (!draft.name.trim() || !draft.condition.trim()) return;
    onSave({ ...draft, name: draft.name.trim(), condition: draft.condition.trim() });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">{mode === "create" ? "Add Rule" : "Edit Rule"}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {mode === "create"
                ? "Define a condition, action, and severity for this policy."
                : "Modify condition, action, and severity for this policy rule."}
            </p>
          </div>
          <Button variant="outline" size="sm" className="h-8 w-8 p-0" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <label className={labelClass} htmlFor="rule-name">
              Name
            </label>
            <input
              id="rule-name"
              value={draft.name}
              onChange={(e) => setDraft((prev) => ({ ...prev, name: e.target.value }))}
              className={inputClass}
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-1.5">
              <label className={labelClass} htmlFor="rule-condition">
                Condition
              </label>
              <PolicyConditionHelpButton
                onApplyExample={(example: PolicyConditionHelpExample) => {
                  setDraft((prev) => ({
                    ...prev,
                    condition: example.condition,
                    action: example.action,
                    severity: example.severity as PolicyRule["severity"],
                    name: prev.name.trim() || example.title,
                  }));
                }}
              />
            </div>
            <textarea
              id="rule-condition"
              value={draft.condition}
              onChange={(e) => setDraft((prev) => ({ ...prev, condition: e.target.value }))}
              rows={3}
              placeholder="prompt.contains('ignore previous')"
              className={cn(inputClass, "h-auto py-2 font-mono text-xs")}
            />
            <p className="text-xs text-muted-foreground">
              Expression-style condition stored with the policy. Example:{" "}
              <code className="rounded bg-muted px-1">prompt.contains(&apos;ignore previous&apos;)</code>
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className={labelClass} htmlFor="rule-action">
                Action
              </label>
              <select
                id="rule-action"
                value={draft.action}
                onChange={(e) => setDraft((prev) => ({ ...prev, action: e.target.value }))}
                className={inputClass}
              >
                {RULE_ACTIONS.map((action) => (
                  <option key={action} value={action}>
                    {action}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className={labelClass} htmlFor="rule-severity">
                Severity
              </label>
              <select
                id="rule-severity"
                value={draft.severity}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, severity: e.target.value as PolicyRule["severity"] }))
                }
                className={inputClass}
              >
                {RULE_SEVERITIES.map((severity) => (
                  <option key={severity} value={severity}>
                    {severity}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(e) => setDraft((prev) => ({ ...prev, enabled: e.target.checked }))}
              className="h-4 w-4 rounded border-input"
            />
            Rule enabled
          </label>
        </div>

        <div className="mt-6 flex justify-between gap-2">
          {mode === "edit" && onDelete ? (
            <Button variant="outline" className="text-red-400 hover:text-red-300" onClick={onDelete}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={!draft.name.trim() || !draft.condition.trim()}>
              {mode === "create" ? "Add Rule" : "Save Rule"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function PolicyTreeItem({
  node,
  depth = 0,
  selectedId,
  onSelect,
}: {
  node: PolicyTreeNode;
  depth?: number;
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedId === node.id;

  return (
    <div>
      <button
        type="button"
        onClick={() => {
          if (node.type === "policy") onSelect(node.id);
          if (hasChildren) setExpanded(!expanded);
        }}
        className={cn(
          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted/60",
          isSelected && "bg-primary/10 text-primary"
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {hasChildren ? (
          expanded ? <ChevronDown className="h-3.5 w-3.5 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 shrink-0" />
        ) : (
          <span className="w-3.5" />
        )}
        {node.type === "folder" ? (
          <Folder className="h-4 w-4 shrink-0 text-amber-400" />
        ) : (
          <FileText className="h-4 w-4 shrink-0 text-primary" />
        )}
        <span className="flex-1 truncate">{node.label}</span>
        {node.status && (
          <Badge
            variant={node.status === "active" ? "success" : node.status === "draft" ? "warning" : "secondary"}
            className="text-[10px]"
          >
            {node.status}
          </Badge>
        )}
      </button>
      {hasChildren && expanded && (
        <div>
          {node.children!.map((child) => (
            <PolicyTreeItem
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

const severityColors = {
  low: "secondary" as const,
  medium: "warning" as const,
  high: "destructive" as const,
  critical: "destructive" as const,
};

function resolveGraphLink(links: PolicyGraphLink[], policyId: string, policyName: string) {
  return (
    links.find((l) => l.policy_id === policyId) ??
    links.find((l) => l.policy_name === policyName) ??
    null
  );
}

export function PolicyStudioLayout() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const policyFromUrl = searchParams.get("policy");
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const canEdit = user?.role === "tenant_admin" || user?.role === "security_admin";
  const { data: treeFromApi = [], invalidatePolicyTree } = usePolicyTree();
  const { data: graphLinks = [] } = usePolicyGraphLinks();

  const [localTree, setLocalTree] = useState<PolicyTreeNode[] | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [testerOpen, setTesterOpen] = useState(false);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const tree = localTree ?? treeFromApi;

  const defaultPolicy = useMemo(() => findFirstPolicy(tree), [tree]);
  const [manualSelectedId, setManualSelectedId] = useState<string | null>(null);
  const selectedId = policyFromUrl ?? manualSelectedId ?? defaultPolicy?.id ?? "";
  const selectedPolicy = findPolicyInTree(tree, selectedId);
  const activePolicyId = selectedPolicy?.type === "policy" ? selectedId : undefined;
  const { data: rules = [], invalidatePolicyRules } = usePolicyRules(activePolicyId);
  const [ruleOverrides, setRuleOverrides] = useState<Record<string, PolicyRule>>({});
  const [addedRules, setAddedRules] = useState<PolicyRule[]>([]);
  const [deletedRuleIds, setDeletedRuleIds] = useState<Set<string>>(() => new Set());
  const [ruleOrderByPolicy, setRuleOrderByPolicy] = useState<Record<string, string[]>>({});
  const [viewMode, setViewMode] = useState<PolicyViewMode>("list");
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [editingRule, setEditingRule] = useState<PolicyRule | null>(null);
  const [ruleEditorMode, setRuleEditorMode] = useState<"create" | "edit">("edit");
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loadingStarter, setLoadingStarter] = useState(false);
  const [policyStatus, setPolicyStatus] = useState<PolicyTreeNode["status"]>("draft");
  const [currentPage, setCurrentPage] = useState(1);
  const RULES_PER_PAGE = 5;

  // Clear unsaved changes and reset pagination when selecting a new policy.
  useEffect(() => {
    setAddedRules([]);
    setDeletedRuleIds(new Set());
    setRuleOverrides({});
    setSelectedRuleId(null);
    setEditingRule(null);
    setSaveNotice(null);
    setSaveError(null);
    setPolicyStatus(selectedPolicy?.status ?? "draft");
    setViewMode("list");
    setCurrentPage(1);
  }, [activePolicyId, selectedPolicy?.status]);

  const baseRules = useMemo(() => {
    const persisted = rules
      .filter((rule) => !deletedRuleIds.has(rule.id))
      .map((rule) => ruleOverrides[rule.id] ?? rule);
    const created = addedRules.map((rule) => ruleOverrides[rule.id] ?? rule);
    return [...persisted, ...created];
  }, [rules, ruleOverrides, addedRules, deletedRuleIds]);

  const displayRules = useMemo(
    () => orderRules(baseRules, ruleOrderByPolicy[selectedId]),
    [baseRules, ruleOrderByPolicy, selectedId]
  );

  const totalPages = Math.max(1, Math.ceil(displayRules.length / RULES_PER_PAGE));
  const paginatedRules = useMemo(() => {
    const start = (currentPage - 1) * RULES_PER_PAGE;
    return displayRules.slice(start, start + RULES_PER_PAGE);
  }, [displayRules, currentPage]);

  const selectedPolicyForGraph = selectedPolicy;
  const graphLink = selectedPolicyForGraph
    ? resolveGraphLink(graphLinks, selectedId, selectedPolicyForGraph.label)
    : null;

  async function handleSaveChanges() {
    if (!token || !canEdit || !activePolicyId) return;
    setSaving(true);
    setSaveError(null);
    try {
      await api.savePolicyRules(token, activePolicyId, {
        rules: displayRules.map((rule) => ({
          id: rule.id,
          name: rule.name,
          condition: rule.condition,
          action: rule.action,
          severity: rule.severity,
          enabled: rule.enabled,
        })),
      });
      setRuleOverrides({});
      setAddedRules([]);
      setDeletedRuleIds(new Set());
      invalidatePolicyRules();
      setSaveNotice("Policy rules saved.");
      toast.success("Policy rules saved successfully.");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to save policy rules";
      setSaveError(msg);
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  }

  function handleAddRule() {
    setRuleEditorMode("create");
    setEditingRule(createEmptyRule());
  }

  function handleRuleSave(updated: PolicyRule) {
    if (ruleEditorMode === "create") {
      setAddedRules((prev) => [...prev, updated]);
      setSelectedRuleId(updated.id);
      toast.success("New rule added. Click Save Changes to persist.");
    } else {
      setRuleOverrides((prev) => ({ ...prev, [updated.id]: updated }));
      toast.success("Rule updated. Click Save Changes to persist.");
    }
    setEditingRule(null);
    setSaveNotice("Rule updated. Click Save Changes to persist.");
  }

  function handleRuleDelete(ruleId: string) {
    if (addedRules.some((rule) => rule.id === ruleId)) {
      setAddedRules((prev) => prev.filter((rule) => rule.id !== ruleId));
    } else {
      setDeletedRuleIds((prev) => new Set(prev).add(ruleId));
    }
    setRuleOverrides((prev) => {
      const next = { ...prev };
      delete next[ruleId];
      return next;
    });
    setEditingRule(null);
    if (selectedRuleId === ruleId) {
      setSelectedRuleId(null);
    }
    setSaveNotice("Rule removed. Click Save Changes to persist.");
    toast.success("Rule removed. Click Save Changes to persist.");
  }

  function handleEditRule(rule: PolicyRule) {
    setRuleEditorMode("edit");
    setEditingRule(rule);
  }

  function handleRuleReorder(ruleIds: string[]) {
    setRuleOrderByPolicy((prev) => ({ ...prev, [selectedId]: ruleIds }));
    setSaveNotice("Rule order updated. Click Save Changes to persist.");
    toast.success("Rule order updated.");
  }

  function handlePolicySelect(id: string) {
    setManualSelectedId(id);
    setSelectedRuleId(null);
  }

  async function handlePolicyStatusChange(nextStatus: PolicyTreeNode["status"]) {
    if (!token || !canEdit || !activePolicyId || !nextStatus) return;
    setPolicyStatus(nextStatus);
    setSaveError(null);
    try {
      await api.updatePolicy(token, activePolicyId, { status: nextStatus });
      invalidatePolicyTree();
      setSaveNotice(`Policy status set to ${nextStatus}.`);
      toast.success(`Policy status set to ${nextStatus}.`);
    } catch (err) {
      setPolicyStatus(selectedPolicy?.status ?? "draft");
      const msg = err instanceof ApiError ? err.message : "Failed to update policy status";
      setSaveError(msg);
      toast.error(msg);
    }
  }

  async function handleLoadStarterRules() {
    if (!token || !canEdit || !activePolicyId) return;
    setLoadingStarter(true);
    setSaveError(null);
    try {
      const result = await api.seedStarterPolicyRules(token, activePolicyId);
      if (result.policies_updated > 0) {
        invalidatePolicyRules();
        setSaveNotice(result.message);
        toast.success(result.message);
      } else {
        const msg = "No starter template available for this policy, or rules already exist.";
        setSaveNotice(msg);
        toast.error(msg);
      }
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to load starter rules";
      setSaveError(msg);
      toast.error(msg);
    } finally {
      setLoadingStarter(false);
    }
  }

  function handlePolicyCreated(node: PolicyTreeNode, parentId: string | null) {
    if (token && canEdit) {
      invalidatePolicyTree();
    } else {
      setLocalTree((prev) => insertPolicyNode(prev ?? treeFromApi, node, parentId));
    }
    toast.success(`${node.type === "policy" ? "Policy" : "Folder"} "${node.label}" created successfully.`);
    if (node.type === "policy") {
      setManualSelectedId(node.id);
      router.replace(`/policy-studio?policy=${encodeURIComponent(node.id)}`, { scroll: false });
    }
  }

  const [activeStudioTab, setActiveStudioTab] = useState<"policies" | "intents">("policies");

  function handleApplyAiSuggestion(rule: PolicyRule) {
    setAddedRules((prev) => [...prev, rule]);
    setSelectedRuleId(rule.id);
    setSaveNotice("Suggested rule added. Click Save Changes to persist.");
    toast.success("Suggested rule added. Click Save Changes to persist.");
  }

  return (
    <div className="space-y-4">
      {/* Top Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-border/60 pb-3">
        <Button
          variant={activeStudioTab === "policies" ? "secondary" : "ghost"}
          size="sm"
          className="gap-2"
          onClick={() => setActiveStudioTab("policies")}
        >
          <ShieldCheck className="h-4 w-4 text-primary" />
          Policy Tree & Rules
        </Button>
        <Button
          variant={activeStudioTab === "intents" ? "secondary" : "ghost"}
          size="sm"
          className="gap-2"
          onClick={() => setActiveStudioTab("intents")}
        >
          <Sparkles className="h-4 w-4 text-purple-400" />
          Custom Intent Classifiers
        </Button>
        <div className="ml-auto">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => setTemplateModalOpen(true)}
          >
            <ShieldCheck className="h-4 w-4 text-green-500" />
            Compliance Templates
          </Button>
        </div>
      </div>

      {activeStudioTab === "intents" ? (
        <CustomIntentsPanel />
      ) : (
        <div className="flex h-[calc(100vh-11rem)] gap-4">
          <Card className="w-72 shrink-0 border-border/60 bg-card/50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Policy Tree</CardTitle>
                <Button size="sm" className="h-7 text-xs" onClick={() => setCreateOpen(true)}>
                  Create
                </Button>
              </div>
            </CardHeader>
            <CardContent className="max-h-[calc(100%-4rem)] overflow-y-auto pt-0">
              {tree.map((node) => (
                <PolicyTreeItem key={node.id} node={node} selectedId={selectedId} onSelect={handlePolicySelect} />
              ))}
            </CardContent>
          </Card>

      <PolicyCreateModal
        open={createOpen}
        tree={tree}
        token={token}
        canEdit={canEdit}
        onClose={() => setCreateOpen(false)}
        onCreated={handlePolicyCreated}
      />

      <Card className="flex-1 flex flex-col overflow-hidden border-border/60 bg-card/50">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>{selectedPolicy?.label ?? "Select a policy"}</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                {graphLink?.description ?? "Select a policy from the tree to view and edit rules."}
              </p>
              {graphLink && (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="gap-1">
                    <GitBranch className="h-3 w-3" />
                    Graph: {graphLink.graph_node_label}
                  </Badge>
                  {graphLink.edge_labels.map((edge) => (
                    <Badge key={edge} variant="secondary" className="text-[10px] capitalize">
                      {edge}
                    </Badge>
                  ))}
                </div>
              )}
              {selectedPolicy?.type === "policy" && (
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <label className="text-xs font-medium text-muted-foreground" htmlFor="policy-status-select">
                    Policy status
                  </label>
                  <select
                    id="policy-status-select"
                    className="h-8 rounded-md border border-input bg-background px-2 text-sm capitalize"
                    value={policyStatus ?? "draft"}
                    onChange={(e) => handlePolicyStatusChange(e.target.value as PolicyTreeNode["status"])}
                    disabled={!canEdit || !activePolicyId}
                  >
                    {POLICY_STATUSES.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex rounded-md border border-border/60 p-0.5">
                <Button
                  variant={viewMode === "list" ? "secondary" : "ghost"}
                  size="sm"
                  className="h-7 gap-1.5 text-xs"
                  onClick={() => setViewMode("list")}
                >
                  <List className="h-3.5 w-3.5" />
                  List
                </Button>
                <Button
                  variant={viewMode === "flow" ? "secondary" : "ghost"}
                  size="sm"
                  className="h-7 gap-1.5 text-xs"
                  onClick={() => setViewMode("flow")}
                >
                  <Workflow className="h-3.5 w-3.5" />
                  Flow
                </Button>
              </div>
              {graphLink && (
                <Button variant="outline" size="sm" className="gap-1.5" asChild>
                  <Link href={graphUrlForPolicy(graphLink)}>
                    <GitBranch className="h-3.5 w-3.5" />
                    View in Graph
                  </Link>
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={() => setTesterOpen(true)}>
                Test Policy
              </Button>
            </div>
          </div>
          {saveNotice && <p className="mt-2 text-sm text-emerald-400">{saveNotice}</p>}
          {saveError && <p className="mt-2 text-sm text-red-400">{saveError}</p>}
        </CardHeader>

        {activePolicyId && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 bg-muted/10 px-6 py-3">
            <div>
              <p className="text-sm font-medium">Policy rules</p>
              <p className="text-xs text-muted-foreground">
                {displayRules.length} rule{displayRules.length === 1 ? "" : "s"} ·{" "}
                {displayRules.filter((rule) => rule.enabled).length} active
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {displayRules.length === 0 &&
                selectedPolicy?.label &&
                STARTER_POLICY_NAMES.has(selectedPolicy.label) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleLoadStarterRules}
                    disabled={!canEdit || loadingStarter}
                  >
                    {loadingStarter ? "Loading…" : "Load starter rules"}
                  </Button>
                )}
              <Button size="sm" className="gap-1.5" onClick={handleAddRule} disabled={!canEdit || !activePolicyId}>
                <Plus className="h-3.5 w-3.5" />
                Add Rule
              </Button>
              <Button size="sm" variant="secondary" onClick={handleSaveChanges} disabled={!canEdit || saving || !activePolicyId}>
                {saving ? "Saving…" : "Save Changes"}
              </Button>
            </div>
          </div>
        )}

        <CardContent className="pt-4 flex-1 overflow-y-auto">
          {viewMode === "flow" ? (
            <PolicyFlowCanvas
              rules={displayRules}
              graphLink={graphLink}
              selectedRuleId={selectedRuleId}
              onRuleSelect={setSelectedRuleId}
              onRuleReorder={handleRuleReorder}
              onEditRule={handleEditRule}
              onAddRule={handleAddRule}
              canEdit={canEdit && Boolean(activePolicyId)}
            />
          ) : displayRules.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border/60 bg-muted/10 px-6 py-16 text-center">
              <p className="text-sm font-medium">No rules configured</p>
              <p className="mt-1 max-w-md text-sm text-muted-foreground">
                This policy has no rules yet. Add a rule to define conditions, actions, and severity, then click Save
                Changes.
              </p>
              <Button className="mt-4 gap-1.5" onClick={handleAddRule} disabled={!canEdit || !activePolicyId}>
                <Plus className="h-4 w-4" />
                Add your first rule
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="space-y-3">
                {paginatedRules.map((rule) => (
                  <div
                    key={rule.id}
                    className="flex items-start justify-between rounded-lg border border-border/60 bg-muted/20 p-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{rule.name}</span>
                        <Badge variant={severityColors[rule.severity]}>{rule.severity}</Badge>
                        {!rule.enabled && <Badge variant="outline">Disabled</Badge>}
                      </div>
                      <p className="font-mono text-xs text-muted-foreground">{rule.condition}</p>
                      <p className="text-sm">
                        Action: <span className="font-medium text-primary">{rule.action}</span>
                      </p>
                    </div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" onClick={() => handleEditRule(rule)} disabled={!canEdit}>
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-400 hover:text-red-300"
                        onClick={() => handleRuleDelete(rule.id)}
                        disabled={!canEdit}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-2">
                  <span className="text-xs text-muted-foreground">
                    Page {currentPage} of {totalPages}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {activePolicyId && (
        <PolicyAiHelper
          token={token}
          policyName={selectedPolicy?.label}
          existingRules={displayRules}
          canEdit={canEdit}
          onApplySuggestion={handleApplyAiSuggestion}
        />
      )}

      {editingRule && (
        <PolicyRuleEditorModal
          key={editingRule.id}
          rule={editingRule}
          mode={ruleEditorMode}
          onClose={() => setEditingRule(null)}
          onSave={handleRuleSave}
          onDelete={ruleEditorMode === "edit" ? () => handleRuleDelete(editingRule.id) : undefined}
        />
      )}

      <PolicyTesterModal 
        isOpen={testerOpen}
        onClose={() => setTesterOpen(false)}
        rules={displayRules.filter(r => r.enabled)}
      />

      <ComplianceTemplateModal
        open={templateModalOpen}
        onClose={() => setTemplateModalOpen(false)}
        token={token}
        onSuccess={(msg) => {
          setSaveNotice(msg);
          invalidatePolicyTree();
        }}
      />
        </div>
      )}
    </div>
  );
}
