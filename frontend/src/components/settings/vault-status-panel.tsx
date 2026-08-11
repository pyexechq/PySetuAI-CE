"use client";

import { useQuery } from "@tanstack/react-query";
import { Loader2, Shield } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function VaultStatusPanel() {
  const token = useAuthStore((s) => s.token);

  const { data, isLoading } = useQuery({
    queryKey: ["vault-status", token],
    queryFn: () => api.getVaultStatus(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Shield className="h-4 w-4" />
          Secrets Backend (Vault)
        </CardTitle>
        <CardDescription>Production secret storage and JWT bootstrap status</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading || !data ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Checking Vault…
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            <StatusRow label="Backend" value={data.secrets_backend} />
            <StatusRow label="Vault enabled" value={data.enabled ? "Yes" : "No"} />
            <StatusRow label="Authenticated" value={data.authenticated ? "Yes" : "No"} />
            <StatusRow label="JWT from Vault" value={data.jwt_from_vault ? "Yes" : "No"} />
            <div className="sm:col-span-2 flex flex-wrap items-center gap-2">
              <span className="text-sm text-muted-foreground">JWT security</span>
              <Badge variant={data.jwt_secret_insecure ? "warning" : "success"}>
                {data.jwt_secret_insecure ? "Insecure dev default" : "OK"}
              </Badge>
            </div>
            {data.error && <p className="text-xs text-red-400 sm:col-span-2">Error: {data.error}</p>}
            <p className="text-xs text-muted-foreground sm:col-span-2">
              Enable with <code className="rounded bg-muted px-1">VAULT_ENABLED=true</code> and run{" "}
              <code className="rounded bg-muted px-1">scripts/vault-setup-approle.sh</code>.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}
