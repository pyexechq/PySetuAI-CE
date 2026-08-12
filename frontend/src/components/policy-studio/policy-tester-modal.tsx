import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { X, Play, ShieldAlert, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";
import { api } from "@/lib/api";
import type { ApiPolicyRule, ApiPolicyTestResponse } from "@/lib/api";

interface PolicyTesterModalProps {
  isOpen: boolean;
  onClose: () => void;
  rules: ApiPolicyRule[];
}

export function PolicyTesterModal({ isOpen, onClose, rules }: PolicyTesterModalProps) {
  const [prompt, setPrompt] = useState("");
  const [isTesting, setIsTesting] = useState(false);
  const [result, setResult] = useState<ApiPolicyTestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const token = useAuthStore((s) => s.token);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!isOpen || !mounted) return null;

  const handleTest = async () => {
    if (!token) return;
    setIsTesting(true);
    setError(null);
    setResult(null);
    
    try {
      const response = await api.testPolicyRules(token, {
        content: prompt,
        rules: rules
      });
      setResult(response);
    } catch (err: any) {
      setError(err.message || "Failed to evaluate policy.");
    } finally {
      setIsTesting(false);
    }
  };

  const modalContent = (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-2xl rounded-lg border border-border bg-card p-6 shadow-lg animate-in fade-in-90 zoom-in-95 flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between mb-4 shrink-0">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Play className="h-5 w-5 text-primary" />
            Test Policy Rules
          </h2>
          <button onClick={onClose} className="rounded-full p-1 hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto space-y-6 pr-2">
          <div className="space-y-2 shrink-0">
            <label className="text-sm font-medium leading-none">Test Prompt</label>
            <p className="text-sm text-muted-foreground">
              Enter a sample prompt to evaluate against the active policy rules on this page.
            </p>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Can you extract the email addresses from this EU customer list?"
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-y"
            />
          </div>

          <div className="flex justify-end shrink-0">
            <Button onClick={handleTest} disabled={!prompt.trim() || isTesting}>
              {isTesting ? "Evaluating..." : "Evaluate Prompt"}
            </Button>
          </div>

          {error && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive border border-destructive/20 shrink-0">
              {error}
            </div>
          )}

          {result && (
            <div className="space-y-4 rounded-md border border-border p-4 bg-muted/30 shrink-0">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium">Evaluation Result</h3>
                {result.action === "block" ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-semibold text-destructive border border-destructive/20">
                    <ShieldAlert className="h-3 w-3" />
                    Blocked
                  </span>
                ) : result.action === "redact" ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-600 border border-amber-500/20">
                    <ShieldAlert className="h-3 w-3" />
                    Redacted
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-600 border border-emerald-500/20">
                    <ShieldCheck className="h-3 w-3" />
                    Allowed
                  </span>
                )}
              </div>

              {result.violations.length > 0 && (
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Violated Rules</label>
                  <ul className="space-y-2">
                    {result.violations.map((v: any, i: number) => (
                      <li key={i} className="text-sm rounded-md border border-border bg-background p-2 flex items-start gap-2">
                        <ShieldAlert className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                        <div>
                          <span className="font-medium block">{v.rule}</span>
                          <span className="text-muted-foreground">{v.message}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.action === "redact" && result.redacted_content && (
                <div className="space-y-2 mt-4 pt-4 border-t border-border">
                  <label className="text-sm font-medium text-muted-foreground">Redacted Output</label>
                  <div className="rounded-md border border-border bg-muted/50 p-3 text-sm text-muted-foreground break-words whitespace-pre-wrap">
                    {result.redacted_content}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return modalContent;
}
