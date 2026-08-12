"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Copy, Loader2, Link2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function McpMultiplexCard() {
  const token = useAuthStore((s) => s.token);
  const [copied, setCopied] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["mcp-multiplex", token],
    queryFn: () => api.getMcpMultiplexInfo(token!),
    enabled: Boolean(token),
  });

  async function copyUrl() {
    if (!data?.url) return;
    try {
      await navigator.clipboard.writeText(data.url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  if (isLoading || !data) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading multiplex URL…
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Link2 className="h-4 w-4 text-sky-400" />
          MCP multiplex URL
        </CardTitle>
        <CardDescription>
          One gateway URL for every registered MCP server. Agents keep the same client API key used for chat completions.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-xs">
            {data.url}
          </code>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={copyUrl}>
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          {data.server_count} servers · {data.tool_count} tools · namespace {data.tool_namespace}
        </p>
        {data.sample_tools.length > 0 ? (
          <p className="text-xs text-muted-foreground">Sample: {data.sample_tools.join(", ")}</p>
        ) : (
          <p className="text-xs text-muted-foreground">Discover tools on a server to populate the multiplex catalog.</p>
        )}
        <p className="text-xs text-muted-foreground">{data.instructions}</p>
      </CardContent>
    </Card>
  );
}
