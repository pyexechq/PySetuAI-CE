import { AppShell } from "@/components/layout/app-shell";
import { SecurityAnalyticsView } from "@/components/security/security-analytics-view";

export default function SecurityPage() {
  return (
    <AppShell
      title="Security Analytics"
      description="Prompt injection, jailbreak, and data exfiltration detection trends"
    >
      <SecurityAnalyticsView />
    </AppShell>
  );
}
