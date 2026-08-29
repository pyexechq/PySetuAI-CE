"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Info, Loader2, Mail, Send, Server, ShieldCheck, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ApiError, api, type ApiSmtpConfig, type ApiSmtpTestResponse } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function SmtpSettingsPanel() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const [config, setConfig] = useState<ApiSmtpConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");
  const [testResult, setTestResult] = useState<ApiSmtpTestResponse | null>(null);

  // Form states
  const [enabled, setEnabled] = useState(false);
  const [host, setHost] = useState("");
  const [port, setPort] = useState(587);
  const [fromEmail, setFromEmail] = useState("");
  const [fromName, setFromName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [useTls, setUseTls] = useState(true);
  const [useSsl, setUseSsl] = useState(false);
  const [testRecipient, setTestRecipient] = useState("");

  const loadConfig = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.getTenantSmtp(token);
      setConfig(data);
      setEnabled(data.enabled);
      setHost(data.host || "");
      setPort(data.port || 587);
      setFromEmail(data.from_email || "");
      setFromName(data.from_name || "");
      setUsername(data.username || "");
      setPassword("");
      setUseTls(data.use_tls);
      setUseSsl(data.use_ssl);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load SMTP configuration");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadConfig();
  }, [loadConfig]);

  useEffect(() => {
    if (user?.email && !testRecipient) {
      setTestRecipient(user.email);
    }
  }, [user?.email]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setError("");
    setSaveSuccess("");
    setTestResult(null);

    try {
      const updated = await api.updateTenantSmtp(token, {
        enabled,
        host,
        port: Number(port),
        from_email: fromEmail,
        from_name: fromName,
        username,
        password: password || undefined,
        use_tls: useTls,
        use_ssl: useSsl,
      });
      setConfig(updated);
      setPassword("");
      setSaveSuccess("SMTP configuration updated successfully.");
      setTimeout(() => setSaveSuccess(""), 4000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update SMTP settings");
    } finally {
      setSaving(false);
    }
  }

  async function handleTest(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !testRecipient) return;
    setTesting(true);
    setTestResult(null);
    setError("");

    try {
      const result = await api.testTenantSmtp(token, {
        recipient_email: testRecipient,
        host: host || undefined,
        port: Number(port) || undefined,
        from_email: fromEmail || undefined,
        from_name: fromName || undefined,
        username: username || undefined,
        password: password || undefined,
        use_tls: useTls,
        use_ssl: useSsl,
      });
      setTestResult(result);
    } catch (err) {
      setTestResult({
        success: false,
        message: err instanceof ApiError ? err.message : "Test request failed",
      });
    } finally {
      setTesting(false);
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12 text-sm text-muted-foreground">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Loading SMTP settings…
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Mail className="h-5 w-5 text-primary" />
                Tenant SMTP & Outbound Email
              </CardTitle>
              <CardDescription className="mt-1">
                Configure your organization's custom mail server for invites, governance notifications, and alert broadcasts.
              </CardDescription>
            </div>
            <div>
              {config?.is_custom ? (
                <Badge variant="default" className="gap-1 bg-emerald-600/10 text-emerald-400 border-emerald-500/20">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Custom Tenant SMTP Active
                </Badge>
              ) : (
                <Badge variant="secondary" className="gap-1">
                  <Server className="h-3.5 w-3.5" />
                  Platform Default SMTP ({config?.source})
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {config?.info_message && (
            <div className="mb-6 flex items-start gap-3 rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground">
              <Info className="mt-0.5 h-4 w-4 text-primary shrink-0" />
              <span>{config.info_message}</span>
            </div>
          )}

          <form onSubmit={handleSave} className="space-y-6">
            <label className="flex items-center justify-between rounded-lg border border-border/60 p-4 cursor-pointer">
              <div className="space-y-0.5">
                <span className="text-sm font-medium">Enable Custom Tenant SMTP</span>
                <p className="text-xs text-muted-foreground">
                  When enabled, all transactional emails from this tenant will be routed through your dedicated server.
                </p>
              </div>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-input text-primary focus:ring-2 focus:ring-ring"
              />
            </label>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="host" className="text-sm font-medium">SMTP Host</label>
                <input
                  id="host"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                  placeholder="e.g. smtp.office365.com or smtp.sendgrid.net"
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                  required={enabled}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="port" className="text-sm font-medium">SMTP Port</label>
                <input
                  id="port"
                  type="number"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                  placeholder="587"
                  value={port}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setPort(val);
                    if (val === 465) {
                      setUseSsl(true);
                      setUseTls(false);
                    } else if (val === 587 || val === 25) {
                      setUseSsl(false);
                      setUseTls(val === 587);
                    }
                  }}
                  required={enabled}
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="fromEmail" className="text-sm font-medium">From Email Address</label>
                <input
                  id="fromEmail"
                  type="email"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                  placeholder="e.g. ai-governance@acme.com"
                  value={fromEmail}
                  onChange={(e) => setFromEmail(e.target.value)}
                  required={enabled}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="fromName" className="text-sm font-medium">Sender Name</label>
                <input
                  id="fromName"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                  placeholder="e.g. Acme AI Governance"
                  value={fromName}
                  onChange={(e) => setFromName(e.target.value)}
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="username" className="text-sm font-medium">SMTP Username</label>
                <input
                  id="username"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                  placeholder="e.g. apikey or user@acme.com"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium">
                  SMTP Password{" "}
                  {config?.password_set && (
                    <span className="text-xs font-normal text-muted-foreground">
                      (Configured: {config.password_masked})
                    </span>
                  )}
                </label>
                <input
                  id="password"
                  type="password"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                  placeholder={config?.password_set ? "Leave blank to keep existing password" : "Enter SMTP password or API token"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="tenant-encryption-mode" className="text-sm font-medium">Security & Encryption Mode</label>
              <select
                id="tenant-encryption-mode"
                value={useSsl ? "ssl" : useTls ? "tls" : "none"}
                onChange={(e) => {
                  const mode = e.target.value;
                  if (mode === "ssl") {
                    setUseSsl(true);
                    setUseTls(false);
                    if (port === 587) setPort(465);
                  } else if (mode === "tls") {
                    setUseSsl(false);
                    setUseTls(true);
                    if (port === 465) setPort(587);
                  } else {
                    setUseSsl(false);
                    setUseTls(false);
                  }
                }}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
              >
                <option value="tls">STARTTLS (Port 587 / 25 - Standard)</option>
                <option value="ssl">Direct SSL / TLS (Port 465 - Implicit SSL)</option>
                <option value="none">None / Plaintext (Internal relay)</option>
              </select>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}
            {saveSuccess && <p className="text-sm text-emerald-400">{saveSuccess}</p>}

            <Button type="submit" disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving…
                </>
              ) : (
                "Save SMTP Configuration"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Test Connection Card */}
      <Card className="border-border/60">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Send className="h-4 w-4 text-primary" />
            Verify Delivery & Send Test Email
          </CardTitle>
          <CardDescription>
            Dispatch a real test notification to verify your SMTP host connectivity and authentication credentials.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleTest} className="space-y-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="flex-1 min-w-[240px] space-y-1.5">
                <label htmlFor="test-recipient" className="text-sm font-medium">Test Recipient Email</label>
                <input
                  id="test-recipient"
                  type="email"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                  placeholder="admin@yourdomain.com"
                  value={testRecipient}
                  onChange={(e) => setTestRecipient(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" variant="secondary" disabled={testing || !testRecipient}>
                {testing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Testing Delivery…
                  </>
                ) : (
                  "Send Test Email"
                )}
              </Button>
            </div>

            {testResult && (
              <div
                className={`rounded-lg border p-4 text-sm ${
                  testResult.success
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                    : "border-destructive/30 bg-destructive/10 text-destructive"
                }`}
              >
                <div className="flex items-center gap-2 font-medium">
                  {testResult.success ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
                  ) : (
                    <XCircle className="h-5 w-5 text-destructive shrink-0" />
                  )}
                  <span>{testResult.message}</span>
                </div>
              </div>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
