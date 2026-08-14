"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Loader2, Play, Shield } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiRagIngestResponse } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function RagGatewayTester() {
  const token = useAuthStore((s) => s.token);
  const [content, setContent] = useState("Quarterly earnings summary for investors.");
  const [exemptionId, setExemptionId] = useState("");
  const [result, setResult] = useState<ApiRagIngestResponse | null>(null);

  const evaluateMutation = useMutation({
    mutationFn: () =>
      api.evaluateRagMovement(token!, {
        content,
        destination: "embedding",
        operation: "embed",
        exemption_id: exemptionId.trim() || undefined,
      }),
    onSuccess: (data) => {
      setResult({
        allowed: data.allowed,
        blocked_hop: data.allowed ? null : "movement_check",
        hops: [],
        classifications: data.classifications,
        sensitivity_labels: data.sensitivity_labels,
        highest_sensitivity: data.highest_sensitivity,
        vector_id: null,
        upserted: false,
        embedding_source: null,
        evidence_bundle_id: data.evidence_bundle_id,
        note: data.stub_note ?? (data.allowed ? "Movement allowed" : "Movement blocked"),
        exemption_applied: data.exemption_applied,
        exemption_error: data.exemption_error,
      });
    },
  });

  const ingestMutation = useMutation({
    mutationFn: () =>
      api.ingestRagContent(token!, {
        content,
        destination: "pinecone",
        exemption_id: exemptionId.trim() || undefined,
      }),
    onSuccess: setResult,
  });

  const pending = evaluateMutation.isPending || ingestMutation.isPending;

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Governed RAG console
        </CardTitle>
        <CardDescription>
          Test DLP classification and OPA data-movement policy before content reaches embeddings or Pinecone.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={5}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="Paste document content to evaluate or ingest…"
        />
        <div className="space-y-1">
          <label className="text-sm font-medium">Break-glass exemption ID (optional)</label>
          <input
            value={exemptionId}
            onChange={(e) => setExemptionId(e.target.value)}
            placeholder="Paste exemption UUID from Compliance Center"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            disabled={!token || pending}
            onClick={() => evaluateMutation.mutate()}
            className="gap-2"
          >
            {evaluateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Evaluate movement
          </Button>
          <Button disabled={!token || pending} onClick={() => ingestMutation.mutate()} className="gap-2">
            {ingestMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Run conditional ingest
          </Button>
        </div>

        {result && (
          <div className="space-y-3 rounded-lg border border-border/60 p-4 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={result.allowed ? "success" : "destructive"}>
                {result.allowed ? "Allowed" : "Blocked"}
              </Badge>
              {result.highest_sensitivity && <Badge variant="outline">{result.highest_sensitivity}</Badge>}
              {result.evidence_bundle_id && (
                <a href="/compliance" className="text-xs text-sky-400 hover:underline">
                  View evidence in Compliance →
                </a>
              )}
            </div>
            {result.classifications.length > 0 && (
              <p className="text-muted-foreground">Detected: {result.classifications.join(", ")}</p>
            )}
            {result.hops.length > 0 && (
              <div className="space-y-1">
                {result.hops.map((hop) => (
                  <div key={hop.hop} className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="font-medium">{hop.hop}</span>
                    <span className="text-muted-foreground">
                      {hop.movement_from} → {hop.movement_to} ({hop.operation})
                    </span>
                    <Badge variant={hop.allowed ? "secondary" : "destructive"}>{hop.allowed ? "pass" : "block"}</Badge>
                  </div>
                ))}
              </div>
            )}
            {result.note && <p className="text-muted-foreground">{result.note}</p>}
            {result.exemption_error && (
              <p className="text-amber-400">Exemption: {result.exemption_error}</p>
            )}
            {result.exemption_applied && (
              <p className="text-emerald-400">Break-glass exemption applied to this request.</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
