"use client";

import { useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  FileWarning,
  FlaskConical,
  Play,
  Plus,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ApiQADefect, ApiQATestCase } from "@/lib/api";
import { useQACycle, useQADefects, useQAMutations, useQAOverview } from "@/hooks/use-qa-dashboard";

type Tab = "overview" | "cases" | "defects";

const STATUS_OPTIONS = ["not_tested", "pass", "fail", "blocked", "skipped"] as const;

const statusBadge: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" }> = {
  pass: { label: "Pass", variant: "success" },
  fail: { label: "Fail", variant: "destructive" },
  blocked: { label: "Blocked", variant: "warning" },
  skipped: { label: "Skipped", variant: "secondary" },
  not_tested: { label: "Not Tested", variant: "outline" },
};

const severityColor: Record<string, string> = {
  S1: "text-red-400 border-red-500/40 bg-red-500/10",
  S2: "text-orange-400 border-orange-500/40 bg-orange-500/10",
  S3: "text-yellow-400 border-yellow-500/40 bg-yellow-500/10",
  S4: "text-slate-400 border-slate-500/40 bg-slate-500/10",
};

function ProgressRing({ value, size = 72 }: { value: number; size?: number }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  const color = value >= 80 ? "#22c55e" : value >= 50 ? "#eab308" : "#ef4444";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="hsl(var(--muted))" strokeWidth="6" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-sm font-bold">{Math.round(value)}%</div>
    </div>
  );
}

function TestCaseRow({
  testCase,
  onRecord,
  onFileDefect,
  filingDefectId,
}: {
  testCase: ApiQATestCase;
  onRecord: (caseId: string, status: string) => void;
  onFileDefect: (caseId: string) => void;
  filingDefectId: string | null;
}) {
  const badge = statusBadge[testCase.status] ?? statusBadge.not_tested;
  const showGuidance = testCase.status === "fail" && testCase.remediation_hint;

  return (
    <>
      <tr className="border-b border-border/40 hover:bg-muted/20">
        <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{testCase.case_id}</td>
        <td className="px-3 py-2 text-sm">{testCase.module}</td>
        <td className="px-3 py-2 text-sm">{testCase.title}</td>
        <td className="px-3 py-2">
          <Badge variant="outline" className="text-xs">
            {testCase.priority}
          </Badge>
        </td>
        <td className="px-3 py-2">
          <Badge variant={badge.variant}>{badge.label}</Badge>
          {testCase.method === "automated" && testCase.automated_key && (
            <p className="mt-1 text-[10px] text-muted-foreground">automated</p>
          )}
        </td>
        <td className="px-3 py-2">
          <div className="flex flex-wrap gap-1">
            {STATUS_OPTIONS.filter((s) => s !== testCase.status).map((s) => (
              <Button key={s} variant="outline" size="sm" className="h-7 px-2 text-xs" onClick={() => onRecord(testCase.id, s)}>
                {s === "pass" ? "✓" : s === "fail" ? "✗" : s.charAt(0).toUpperCase() + s.slice(1)}
              </Button>
            ))}
            {testCase.status === "fail" && (
              <Button
                variant="secondary"
                size="sm"
                className="h-7 gap-1 px-2 text-xs"
                disabled={filingDefectId === testCase.id}
                onClick={() => onFileDefect(testCase.id)}
              >
                <FileWarning className="h-3 w-3" />
                {filingDefectId === testCase.id ? "Filing…" : "File defect"}
              </Button>
            )}
          </div>
        </td>
      </tr>
      {showGuidance && (
        <tr className="border-b border-border/40 bg-red-500/5">
          <td colSpan={6} className="px-3 py-2">
            <p className="text-xs font-medium text-red-300">Fix guidance</p>
            <p className="mt-1 text-xs text-muted-foreground">{testCase.remediation_hint}</p>
            {testCase.linked_defect_code && (
              <p className="mt-1 text-[10px] text-muted-foreground">
                Related baseline defect: <span className="font-mono">{testCase.linked_defect_code}</span>
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function DefectRow({
  defect,
  onStatusChange,
}: {
  defect: ApiQADefect;
  onStatusChange: (id: string, status: string) => void;
}) {
  return (
    <tr className="border-b border-border/40 hover:bg-muted/20">
      <td className="px-3 py-2 font-mono text-xs">{defect.defect_code}</td>
      <td className="px-3 py-2">
        <span className={cn("rounded border px-1.5 py-0.5 text-xs font-semibold", severityColor[defect.severity])}>
          {defect.severity}
        </span>
      </td>
      <td className="px-3 py-2 text-sm">{defect.module}</td>
      <td className="px-3 py-2 text-sm">{defect.title}</td>
      <td className="px-3 py-2">
        <Badge variant={defect.status === "open" ? "destructive" : "success"}>{defect.status}</Badge>
      </td>
      <td className="px-3 py-2">
        {defect.status === "open" && (
          <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => onStatusChange(defect.id, "fixed")}>
            Mark Fixed
          </Button>
        )}
      </td>
    </tr>
  );
}

export function QADashboardView() {
  const [tab, setTab] = useState<Tab>("overview");
  const [moduleFilter, setModuleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [newCycleName, setNewCycleName] = useState("");
  const [showNewCycle, setShowNewCycle] = useState(false);
  const [automatedResult, setAutomatedResult] = useState<string | null>(null);
  const [filingDefectId, setFilingDefectId] = useState<string | null>(null);

  const { data: overview, isLoading, isError, error, refetch } = useQAOverview();
  const activeCycleId = overview?.active_cycle?.id ?? null;
  const { data: cycleDetail } = useQACycle(activeCycleId);
  const { data: defects = [] } = useQADefects(activeCycleId);
  const { createCycle, updateCycle, updateTestCase, updateDefect, runAutomated, fileDefectFromCase } = useQAMutations();

  const filteredCases = useMemo(() => {
    const cases = cycleDetail?.cases ?? [];
    return cases.filter((c) => {
      if (moduleFilter !== "all" && c.module !== moduleFilter) return false;
      if (statusFilter !== "all" && c.status !== statusFilter) return false;
      return true;
    });
  }, [cycleDetail?.cases, moduleFilter, statusFilter]);

  const modules = useMemo(() => {
    const set = new Set((cycleDetail?.cases ?? []).map((c) => c.module));
    return ["all", ...Array.from(set).sort()];
  }, [cycleDetail?.cases]);

  const failedAutomatableCount = useMemo(() => {
    return (cycleDetail?.cases ?? []).filter((c) => c.status === "fail" && c.automated_key).length;
  }, [cycleDetail?.cases]);

  const handleStartCycle = async (importBaseline: boolean) => {
    const name = newCycleName.trim() || `QA Cycle ${new Date().toLocaleDateString()}`;
    await createCycle.mutateAsync({
      name,
      import_baseline: importBaseline,
      import_baseline_defects: importBaseline,
    });
    setNewCycleName("");
    setShowNewCycle(false);
    setTab("cases");
  };

  const handleRunAutomated = async (scope: "all" | "failed" = "all") => {
    if (!activeCycleId) return;
    const result = await runAutomated.mutateAsync({ cycleId: activeCycleId, scope });
    setAutomatedResult(
      `[${result.scope}] pytest: ${result.tests_passed}/${result.tests_run} passed · ${result.cases_updated} cases updated · ${result.tests_targeted} targeted\n${result.output_tail}`
    );
  };

  const handleFileDefect = async (caseId: string) => {
    setFilingDefectId(caseId);
    try {
      const result = await fileDefectFromCase.mutateAsync(caseId);
      setTab("defects");
      if (!result.created) {
        setAutomatedResult(`Open defect already exists: ${result.defect.defect_code}`);
      }
    } finally {
      setFilingDefectId(null);
    }
  };

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading QA dashboard…</p>;
  }

  if (isError) {
    return (
      <Card className="border-destructive/40 bg-destructive/5">
        <CardContent className="space-y-3 p-6">
          <p className="font-medium text-destructive">Unable to load QA dashboard</p>
          <p className="text-sm text-muted-foreground">
            {(error as Error)?.message ?? "The QA API is unavailable. Rebuild Docker containers after pulling the latest code."}
          </p>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => refetch()}>Retry</Button>
          </div>
          <pre className="rounded-md bg-muted/30 p-3 text-xs text-muted-foreground">
            docker compose up -d --build backend frontend
          </pre>
        </CardContent>
      </Card>
    );
  }

  const cycle = overview?.active_cycle;
  const releaseApproved = cycle?.release_decision === "approved";
  const releaseBlocked = cycle?.release_decision === "not_approved";

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Card className="border-border/60 bg-card/50">
          <CardContent className="flex items-center gap-4 p-5">
            <ProgressRing value={overview?.overall_pass_rate ?? 0} />
            <div>
              <p className="text-sm text-muted-foreground">Pass Rate</p>
              <p className="text-xl font-bold">{overview?.overall_pass_rate ?? 0}%</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              <p className="text-sm text-muted-foreground">Passed</p>
            </div>
            <p className="mt-1 text-2xl font-bold">{cycle?.passed_cases ?? 0}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-red-400">
              <XCircle className="h-4 w-4" />
              <p className="text-sm text-muted-foreground">Failed</p>
            </div>
            <p className="mt-1 text-2xl font-bold">{cycle?.failed_cases ?? 0}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-orange-400">
              <ShieldAlert className="h-4 w-4" />
              <p className="text-sm text-muted-foreground">Open Defects</p>
            </div>
            <p className="mt-1 text-2xl font-bold">{overview?.total_open_defects ?? 0}</p>
            {(overview?.s1_open_defects ?? 0) > 0 && (
              <p className="text-xs text-red-400">{overview?.s1_open_defects} S1 critical</p>
            )}
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="flex items-center gap-2">
              <ClipboardCheck className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Release Gate</p>
            </div>
            <Badge
              className="mt-2"
              variant={releaseApproved ? "success" : releaseBlocked ? "destructive" : "warning"}
            >
              {cycle?.release_decision?.replace("_", " ") ?? "pending"}
            </Badge>
          </CardContent>
        </Card>
      </div>

      {/* Active cycle bar */}
      <Card className="border-border/60 bg-card/50">
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 pb-3">
          <div>
            <CardTitle className="text-base">
              {cycle ? cycle.name : "No active test cycle"}
            </CardTitle>
            {cycle && (
              <p className="text-xs text-muted-foreground">
                {cycle.passed_cases + cycle.failed_cases + cycle.blocked_cases}/{cycle.total_cases} executed ·{" "}
                {cycle.not_tested_cases} remaining
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {!cycle && (
              <>
                <Button size="sm" className="gap-1.5" onClick={() => setShowNewCycle(true)}>
                  <Plus className="h-3.5 w-3.5" />
                  Start Test Cycle
                </Button>
              </>
            )}
            {cycle && cycle.status === "in_progress" && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5"
                  onClick={() => handleRunAutomated("all")}
                  disabled={runAutomated.isPending}
                >
                  <FlaskConical className="h-3.5 w-3.5" />
                  {runAutomated.isPending ? "Running…" : "Run Automated Tests"}
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  className="gap-1.5"
                  onClick={() => handleRunAutomated("failed")}
                  disabled={runAutomated.isPending || failedAutomatableCount === 0}
                  title={
                    failedAutomatableCount === 0
                      ? "No failed automatable cases to retest"
                      : `Retest ${failedAutomatableCount} failed pytest case(s)`
                  }
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Retest Failed
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    updateCycle.mutate({
                      cycleId: cycle.id,
                      body: {
                        release_decision: (overview?.s1_open_defects ?? 0) > 0 ? "not_approved" : "approved",
                        status: "completed",
                      },
                    })
                  }
                >
                  Complete Cycle
                </Button>
              </>
            )}
            {cycle && (
              <Button size="sm" variant="ghost" onClick={() => setShowNewCycle(true)}>
                <Plus className="h-3.5 w-3.5" />
                New Cycle
              </Button>
            )}
          </div>
        </CardHeader>

        {showNewCycle && (
          <CardContent className="border-t border-border/40 pt-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-[240px] flex-1">
                <label className="mb-1 block text-xs text-muted-foreground">Cycle name</label>
                <input
                  value={newCycleName}
                  onChange={(e) => setNewCycleName(e.target.value)}
                  placeholder={`QA Cycle ${new Date().toLocaleDateString()}`}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                />
              </div>
              <Button size="sm" onClick={() => handleStartCycle(false)} disabled={createCycle.isPending}>
                Start Empty
              </Button>
              <Button size="sm" variant="secondary" onClick={() => handleStartCycle(true)} disabled={createCycle.isPending}>
                Start with QA-001 Baseline
              </Button>
            </div>
          </CardContent>
        )}

        {automatedResult && (
          <CardContent className="border-t border-border/40 pt-4">
            <pre className="max-h-32 overflow-auto rounded-md bg-muted/30 p-3 text-xs text-muted-foreground">{automatedResult}</pre>
          </CardContent>
        )}
      </Card>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border/60 pb-2">
        {(["overview", "cases", "defects"] as Tab[]).map((t) => (
          <Button key={t} variant={tab === t ? "default" : "ghost"} size="sm" onClick={() => setTab(t)}>
            {t === "overview" ? "Overview" : t === "cases" ? "Test Cases" : "Defects"}
          </Button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle className="text-sm">Modules in Scope</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {(overview?.modules_in_scope ?? []).map((m) => (
                  <Badge key={m} variant="outline">
                    {m}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle className="text-sm">Release Readiness</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span>S1 defects</span>
                <span className={(overview?.s1_open_defects ?? 0) > 0 ? "text-red-400" : "text-emerald-400"}>
                  {(overview?.s1_open_defects ?? 0) === 0 ? "✓ Clear" : `${overview?.s1_open_defects} open`}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>S2 defects</span>
                <span className={(overview?.s2_open_defects ?? 0) > 0 ? "text-orange-400" : "text-emerald-400"}>
                  {(overview?.s2_open_defects ?? 0) === 0 ? "✓ Clear" : `${overview?.s2_open_defects} open`}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Test cycles</span>
                <span>{overview?.total_cycles ?? 0}</span>
              </div>
              {(overview?.s1_open_defects ?? 0) > 0 && (
                <p className="mt-3 flex items-start gap-2 rounded-md border border-red-500/30 bg-red-500/5 p-3 text-xs text-red-300">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  Release blocked — resolve S1 defects before approving release.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {tab === "cases" && (
        <div className="space-y-3">
          {!cycle ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              Start a test cycle to begin recording results.
            </p>
          ) : (
            <>
              <div className="flex flex-wrap gap-2">
                {modules.map((m) => (
                  <Button
                    key={m}
                    variant={moduleFilter === m ? "default" : "outline"}
                    size="sm"
                    onClick={() => setModuleFilter(m)}
                  >
                    {m === "all" ? "All Modules" : m}
                  </Button>
                ))}
                <span className="mx-2 w-px bg-border" />
                {["all", ...STATUS_OPTIONS].map((s) => (
                  <Button
                    key={s}
                    variant={statusFilter === s ? "default" : "outline"}
                    size="sm"
                    onClick={() => setStatusFilter(s)}
                  >
                    {s === "all" ? "All Status" : statusBadge[s]?.label ?? s}
                  </Button>
                ))}
              </div>
              <div className="overflow-x-auto rounded-md border border-border/60">
                <table className="w-full min-w-[800px] text-left">
                  <thead className="bg-muted/30 text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2">ID</th>
                      <th className="px-3 py-2">Module</th>
                      <th className="px-3 py-2">Test Case</th>
                      <th className="px-3 py-2">Priority</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Record Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCases.map((tc) => (
                      <TestCaseRow
                        key={tc.id}
                        testCase={tc}
                        onRecord={(id, status) => updateTestCase.mutate({ caseId: id, status })}
                        onFileDefect={handleFileDefect}
                        filingDefectId={filingDefectId}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-muted-foreground">
                Showing {filteredCases.length} of {cycleDetail?.cases.length ?? 0} cases · Record pass/fail, use{" "}
                <strong>File defect</strong> on failures for fix guidance, then <strong>Retest Failed</strong> for automatable cases.
              </p>
            </>
          )}
        </div>
      )}

      {tab === "defects" && (
        <div className="space-y-3">
          <div className="overflow-x-auto rounded-md border border-border/60">
            <table className="w-full min-w-[700px] text-left">
              <thead className="bg-muted/30 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-3 py-2">Code</th>
                  <th className="px-3 py-2">Severity</th>
                  <th className="px-3 py-2">Module</th>
                  <th className="px-3 py-2">Title</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {defects.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center text-sm text-muted-foreground">
                      No defects recorded. Import QA-001 baseline when starting a cycle, or log defects during testing.
                    </td>
                  </tr>
                ) : (
                  defects.map((d) => (
                    <DefectRow
                      key={d.id}
                      defect={d}
                      onStatusChange={(id, status) => updateDefect.mutate({ defectId: id, body: { status } })}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!cycle && tab !== "overview" && (
        <div className="flex flex-col items-center gap-3 py-8">
          <Play className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Start a test cycle to begin manual and automated testing.</p>
          <Button onClick={() => setShowNewCycle(true)}>Start Test Cycle</Button>
        </div>
      )}
    </div>
  );
}
