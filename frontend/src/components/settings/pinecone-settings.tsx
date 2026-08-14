"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Loader2, Save } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiRagGatewaySettings } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const EMPTY: ApiRagGatewaySettings = {
  pinecone_enabled: false,
  pinecone_api_key_set: false,
  pinecone_api_key_masked: null,
  pinecone_host: "",
  pinecone_namespace: "",
  pinecone_dimension: 1536,
  embedding_model: "text-embedding-3-small",
  configured: false,
  config_source: "environment",
  env_fallback_note:
    "Environment variables are used when tenant Pinecone settings are empty. Tenant settings here take priority.",
};

export function PineconeSettingsPanel() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const canEdit = user?.role === "tenant_admin" || user?.role === "security_admin";

  const { data, isLoading } = useQuery({
    queryKey: ["rag-gateway-settings", token],
    queryFn: () => api.getRagGatewaySettings(token!),
    enabled: Boolean(token),
  });

  const settings = data ?? EMPTY;

  if (!token) return null;

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading RAG gateway settings…
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Vector store (Pinecone)
            </CardTitle>
            <CardDescription>
              Governed RAG upserts use this index after DLP classification and OPA data-movement checks pass.
            </CardDescription>
          </div>
          <Badge variant={settings.configured ? "success" : "warning"}>
            {settings.configured ? "Configured" : "Not configured"}
          </Badge>
        </div>
      </CardHeader>
      <PineconeSettingsForm
        key={`${token}-${settings.config_source}-${settings.pinecone_enabled}`}
        settings={settings}
        token={token}
        canEdit={canEdit}
        queryClient={queryClient}
      />
    </Card>
  );
}

function PineconeSettingsForm({
  settings,
  token,
  canEdit,
  queryClient,
}: {
  settings: ApiRagGatewaySettings;
  token: string;
  canEdit: boolean;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const [enabled, setEnabled] = useState(settings.pinecone_enabled);
  const [apiKey, setApiKey] = useState("");
  const [host, setHost] = useState(settings.pinecone_host);
  const [namespace, setNamespace] = useState(settings.pinecone_namespace);
  const [dimension, setDimension] = useState(String(settings.pinecone_dimension));

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateRagGatewaySettings(token, {
        pinecone_enabled: enabled,
        pinecone_api_key: apiKey || undefined,
        pinecone_host: host,
        pinecone_namespace: namespace,
        pinecone_dimension: Number(dimension) || settings.pinecone_dimension,
      }),
    onSuccess: () => {
      setApiKey("");
      queryClient.invalidateQueries({ queryKey: ["rag-gateway-settings"] });
    },
  });

  return (
    <CardContent className="space-y-4">
      <p className="text-xs text-muted-foreground">{settings.env_fallback_note}</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            disabled={!canEdit}
          />
          Enable Pinecone for governed RAG upserts
        </label>
        <div className="text-sm text-muted-foreground">
          Embedding model: <span className="font-medium text-foreground">{settings.embedding_model}</span>
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">API key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={settings.pinecone_api_key_masked ?? "Paste Pinecone API key"}
            disabled={!canEdit}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Index host</label>
          <input
            value={host}
            onChange={(e) => setHost(e.target.value)}
            placeholder="https://your-index.svc.region.pinecone.io"
            disabled={!canEdit}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Namespace</label>
          <input
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
            placeholder="default"
            disabled={!canEdit}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Vector dimension</label>
          <input
            value={dimension}
            onChange={(e) => setDimension(e.target.value)}
            disabled={!canEdit}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>
      </div>
      {canEdit ? (
        <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending} className="gap-2">
          {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save vector store settings
        </Button>
      ) : (
        <p className="text-xs text-muted-foreground">Tenant admin access is required to edit vector store settings.</p>
      )}
    </CardContent>
  );
}
