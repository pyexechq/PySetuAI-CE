import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { ApprovalCenterView } from "@/components/approvals/approval-center-view";

function ApprovalCenterFallback() {
  return (
    <div className="flex min-h-[240px] items-center justify-center text-sm text-muted-foreground">
      Loading approval center…
    </div>
  );
}

export default function ApprovalsPage() {
  return (
    <AppShell
      title="Approval Center"
      description="Review and decide on agent actions that require human sign-off"
    >
      <Suspense fallback={<ApprovalCenterFallback />}>
        <ApprovalCenterView />
      </Suspense>
    </AppShell>
  );
}
