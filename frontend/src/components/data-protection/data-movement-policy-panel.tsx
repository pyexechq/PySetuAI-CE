"use client";

import { Shuffle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataMovementPolicyBody } from "@/components/compliance/data-movement-policy-modal";

interface DataMovementPolicyPanelProps {
  token: string | null;
  canEdit: boolean;
  onSaved: () => void;
}

export function DataMovementPolicyPanel({ token, canEdit, onSaved }: DataMovementPolicyPanelProps) {
  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shuffle className="h-5 w-5" />
          Data-movement policy
        </CardTitle>
        <CardDescription>
          Define which sensitivity labels cannot reach vector destinations. OPA enforces these rules during governed RAG ingest.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <DataMovementPolicyBody token={token} canEdit={canEdit} onSaved={onSaved} />
      </CardContent>
    </Card>
  );
}
