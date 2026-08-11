"use client";

import { useEffect, useRef, useState } from "react";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export type PolicyConditionHelpExample = {
  title: string;
  condition: string;
  description: string;
  action: string;
  severity: string;
};

export const POLICY_CONDITION_HELP: PolicyConditionHelpExample[] = [
  {
    title: "Prompt substring match",
    condition: "prompt.contains('ignore previous')",
    description: "Matches when the user prompt contains a phrase (also matches “ignore all previous”).",
    action: "Block",
    severity: "critical",
  },
  {
    title: "Regex on full content",
    condition: "content.matches(/ignore\\s+(all\\s+)?previous\\s+instructions/i)",
    description: "Use JavaScript-style regex between slashes for flexible pattern matching.",
    action: "Block",
    severity: "critical",
  },
  {
    title: "Jailbreak / DAN pattern",
    condition: "prompt.contains('you are now dan')",
    description: "Blocks common role-play jailbreak attempts that claim an unrestricted persona.",
    action: "Block",
    severity: "critical",
  },
  {
    title: "System prompt exfiltration",
    condition:
      "content.matches(/(reveal|show|print|repeat|output|display)\\s+(me\\s+)?(your\\s+)?(system\\s+)?(prompt|instructions)/i)",
    description: "Blocks requests to reveal hidden system instructions.",
    action: "Block",
    severity: "critical",
  },
  {
    title: "SSN redaction",
    condition: "content.matches(/\\d{3}-\\d{2}-\\d{4}/)",
    description: "Detects US Social Security Number patterns for redaction.",
    action: "Redact",
    severity: "high",
  },
  {
    title: "EU residency gate",
    condition: "region != 'EU' && has_pii",
    description: "Blocks when PII is present and processing region is outside the EU.",
    action: "Block",
    severity: "high",
  },
  {
    title: "PII present",
    condition: "has_pii",
    description: "Matches when the gateway classified content as containing personal data.",
    action: "Alert",
    severity: "medium",
  },
  {
    title: "Cross-border PII alert",
    condition: "has_pii && region != user_region",
    description: "Alerts when PII crosses the user's home region boundary.",
    action: "Alert",
    severity: "medium",
  },
];

export function PolicyConditionHelpButton({
  onApplyExample,
  className,
}: {
  onApplyExample?: (example: PolicyConditionHelpExample) => void;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <div ref={panelRef} className={cn("relative inline-flex", className)}>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
        aria-label="Condition syntax help"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        <HelpCircle className="h-4 w-4" />
      </Button>

      {open && (
        <div className="absolute left-0 top-full z-[60] mt-2 w-[min(24rem,calc(100vw-2rem))] rounded-lg border border-border bg-popover p-3 shadow-xl">
          <p className="text-xs font-semibold text-foreground">Condition examples</p>
          <p className="mt-1 text-[11px] text-muted-foreground">
            HelixGuard evaluates expression-style conditions at the gateway. Click an example to use it in your rule.
          </p>
          <div className="mt-3 max-h-72 space-y-2 overflow-y-auto">
            {POLICY_CONDITION_HELP.map((example) => (
              <button
                key={example.title}
                type="button"
                className="w-full rounded-md border border-border/60 bg-muted/20 p-2 text-left transition-colors hover:bg-muted/40"
                onClick={() => {
                  onApplyExample?.(example);
                  setOpen(false);
                }}
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-xs font-medium">{example.title}</span>
                  <Badge variant="outline" className="text-[10px]">
                    {example.action}
                  </Badge>
                  <Badge variant="secondary" className="text-[10px] capitalize">
                    {example.severity}
                  </Badge>
                </div>
                <code className="mt-1 block break-all font-mono text-[10px] text-primary">{example.condition}</code>
                <p className="mt-1 text-[11px] text-muted-foreground">{example.description}</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
