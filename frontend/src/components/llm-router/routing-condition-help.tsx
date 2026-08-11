"use client";

import { useEffect, useRef, useState } from "react";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export type RoutingConditionHelpExample = {
  title: string;
  condition: string;
  description: string;
};

export const ROUTING_CONDITION_HELP: RoutingConditionHelpExample[] = [
  {
    title: "Code review tasks",
    condition: "task.type == 'code_review'",
    description:
      "Routes when routing_context.task.type is code_review. The gateway can infer this from prompts mentioning code review or PR review.",
  },
  {
    title: "Image / multimodal input",
    condition: "input.has_image == True",
    description:
      "Routes requests that include image attachments or image hints in the prompt. Set input.has_image in routing_context from your client.",
  },
  {
    title: "Latency-sensitive SLA",
    condition: "sla.latency_ms <= 2000",
    description:
      "Use numeric comparisons on dotted paths such as sla.latency_ms when your client passes SLA metadata in routing_context.",
  },
  {
    title: "High priority only",
    condition: "task.priority == 'high'",
    description:
      "Match a custom priority field from routing_context. Pass JSON in the request routing_context or a structured system message.",
  },
  {
    title: "Combine with AND",
    condition: "task.type == 'code_review' and input.has_image == False",
    description: "Combine expressions with and / or. Lowercase and is supported by the router evaluator.",
  },
  {
    title: "Combine with OR",
    condition: "task.type == 'code_review' or task.priority == 'high'",
    description: "First active rule (lowest priority number) that matches wins when model is auto.",
  },
  {
    title: "Exclude images",
    condition: "not input.has_image",
    description: "Unary not is supported for boolean context fields.",
  },
  {
    title: "Catch-all fallback",
    condition: "default",
    description:
      "Always matches. Use as the last rule in the list (highest priority number) to define a default target model for model: auto.",
  },
];

export function RoutingConditionHelpButton({
  onApplyExample,
  className,
}: {
  onApplyExample?: (example: RoutingConditionHelpExample) => void;
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
        aria-label="Routing condition help"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        <HelpCircle className="h-4 w-4" />
      </Button>

      {open && (
        <div className="absolute left-0 top-full z-[60] mt-2 w-[min(24rem,calc(100vw-2rem))] rounded-lg border border-border bg-popover p-3 shadow-xl">
          <p className="text-xs font-semibold text-foreground">Condition examples</p>
          <p className="mt-1 text-[11px] text-muted-foreground">
            Active rules are evaluated when the gateway receives <code className="rounded bg-muted px-1">model: auto</code>.
            Pass context via <code className="rounded bg-muted px-1">routing_context</code> on the request body.
          </p>
          <div className="mt-3 max-h-72 space-y-2 overflow-y-auto">
            {ROUTING_CONDITION_HELP.map((example) => (
              <button
                key={example.title}
                type="button"
                className="w-full rounded-md border border-border/60 bg-muted/20 p-2 text-left transition-colors hover:bg-muted/40"
                onClick={() => {
                  onApplyExample?.(example);
                  setOpen(false);
                }}
              >
                <span className="text-xs font-medium">{example.title}</span>
                <code className="mt-1 block break-all font-mono text-[10px] text-primary">{example.condition}</code>
                <p className="mt-1 text-[11px] text-muted-foreground">{example.description}</p>
              </button>
            ))}
          </div>
          <p className="mt-2 text-[10px] text-muted-foreground">
            Example routing_context:{" "}
            <code className="rounded bg-muted px-1">{`{"task":{"type":"code_review"},"input":{"has_image":false}}`}</code>
          </p>
        </div>
      )}
    </div>
  );
}
