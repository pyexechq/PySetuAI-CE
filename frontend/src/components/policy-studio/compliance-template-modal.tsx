import { ShieldCheck, FileText, Database, Lock, Server } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AppModal } from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { useState } from "react";
import { toast } from "react-hot-toast";

interface ComplianceTemplate {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

const TEMPLATES: ComplianceTemplate[] = [
  {
    id: "gdpr",
    title: "GDPR Privacy Guard",
    description: "Detects and redacts EU citizens' Personally Identifiable Information (PII) before sending to LLMs.",
    icon: <ShieldCheck className="h-6 w-6 text-blue-500" />
  },
  {
    id: "hipaa",
    title: "HIPAA PHI Protection",
    description: "Detects and redacts Protected Health Information (PHI) to maintain HIPAA compliance.",
    icon: <FileText className="h-6 w-6 text-green-500" />
  },
  {
    id: "soc2",
    title: "SOC2 Security Standards",
    description: "Enforces strict security guardrails including Prompt Injection blocking and jailbreak prevention.",
    icon: <Database className="h-6 w-6 text-purple-500" />
  },
  {
    id: "iso27001",
    title: "ISO27001 Access Controls",
    description: "Baseline policies for data residency enforcement, strict topic moderation, and system integrity.",
    icon: <Lock className="h-6 w-6 text-amber-500" />
  },
  {
    id: "nist",
    title: "NIST AI RMF",
    description: "Aligns with NIST AI Risk Management Framework to detect harmful output, bias, and off-topic requests.",
    icon: <Server className="h-6 w-6 text-red-500" />
  }
];

export function ComplianceTemplateModal({
  open,
  onClose,
  token,
  onSuccess,
}: {
  open: boolean;
  onClose: () => void;
  token: string | null;
  onSuccess: (message: string) => void;
}) {
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  async function handleApplyTemplate(template: ComplianceTemplate) {
    if (!token) return;
    setLoading(true);
    try {
      const result = await api.seedComplianceTemplate(token, template.id);
      onSuccess(result.message);
      toast.success(result.message);
      onClose();
    } catch (err: any) {
      toast.error(err.message || "Failed to apply template");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppModal
      title="Compliance Templates"
      description="Kickstart your AI security with industry-standard compliance bundles."
      onClose={onClose}
      size="2xl"
    >
        <div className="grid gap-4 sm:grid-cols-2">
            {TEMPLATES.map((template) => (
              <div
                key={template.id}
                className="flex flex-col justify-between rounded-lg border border-border/60 bg-muted/10 p-5 transition-colors hover:border-border hover:bg-muted/30"
              >
                <div>
                  <div className="mb-3 flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-background border border-border/50">
                      {template.icon}
                    </div>
                    <h3 className="font-medium">{template.title}</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">{template.description}</p>
                </div>
                <div className="mt-6 flex justify-end">
                  <Button size="sm" onClick={() => handleApplyTemplate(template)}>
                    Apply Template
                  </Button>
                </div>
              </div>
            ))}
          </div>
    </AppModal>
  );
}
