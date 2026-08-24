"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  Users, 
  ShieldCheck, 
  Search, 
  CheckCircle2, 
  Clock, 
  XCircle, 
  Trash2, 
  Server, 
  Key, 
  Layers, 
  Filter,
  ExternalLink,
  ChevronRight
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiApprovalRequest } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function McpDeveloperGrantsCard({ canEdit }: { canEdit: boolean }) {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<"all" | "approved" | "pending">("approved");

  const { data: approvals = [], isLoading } = useQuery({
    queryKey: ["mcp-developer-grants", token],
    queryFn: () => api.getApprovals(token!, "all"),
    enabled: Boolean(token),
  });

  const revokeMutation = useMutation({
    mutationFn: (approvalId: string) => 
      api.rejectApproval(token!, approvalId, "Revoked from MCP Governance Access & RBAC"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-developer-grants"] });
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
    },
  });

  const mcpRequests = approvals.filter((a) => a.action === "mcp_access_request" || a.resource === "mcp_catalog");
  
  const approvedGrants = mcpRequests.filter((a) => a.status === "approved");
  const pendingRequests = mcpRequests.filter((a) => a.status === "pending");
  const uniqueUsers = new Set(approvedGrants.map((a) => a.user_name)).size;
  const totalOperations = approvedGrants.reduce(
    (acc, a) => acc + (a.requested_mcp_tools?.length || 1), 
    0
  );

  const filteredGrants = mcpRequests.filter((req) => {
    if (filterStatus === "approved" && req.status !== "approved") return false;
    if (filterStatus === "pending" && req.status !== "pending") return false;

    if (!search) return true;
    const q = search.toLowerCase();
    return (
      req.user_name?.toLowerCase().includes(q) ||
      req.tool?.toLowerCase().includes(q) ||
      req.requested_mcp_tool?.toLowerCase().includes(q) ||
      (req.requested_mcp_tools || []).some((t) => t.toLowerCase().includes(q)) ||
      req.reason?.toLowerCase().includes(q)
    );
  });

  return (
    <Card className="border-border bg-card shadow-sm rounded-xl overflow-hidden">
      <CardHeader className="p-5 pb-4 border-b border-border/70 bg-card/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              Developer Portal MCP Server Access &amp; User Grants
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground mt-1">
              Active users and self-service Developer Portal access requests approved for governed MCP Servers.
            </CardDescription>
          </div>

          {/* Quick Metrics */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-semibold">
              <Users className="w-3.5 h-3.5" />
              <span>{uniqueUsers} Authorized User{uniqueUsers === 1 ? "" : "s"}</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/20 text-primary text-xs font-semibold">
              <Layers className="w-3.5 h-3.5" />
              <span>{approvedGrants.length} Active Grant{approvedGrants.length === 1 ? "" : "s"}</span>
            </div>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 mt-1">
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search user, server, or operation..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8.5 pr-3 py-1.5 text-xs bg-background border border-input rounded-lg placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex items-center gap-1.5 self-end sm:self-auto">
            <Button
              size="sm"
              variant={filterStatus === "approved" ? "secondary" : "ghost"}
              className="h-8 text-xs font-semibold"
              onClick={() => setFilterStatus("approved")}
            >
              <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-500" />
              Approved Grants ({approvedGrants.length})
            </Button>
            <Button
              size="sm"
              variant={filterStatus === "pending" ? "secondary" : "ghost"}
              className="h-8 text-xs font-semibold"
              onClick={() => setFilterStatus("pending")}
            >
              <Clock className="w-3.5 h-3.5 mr-1 text-amber-500" />
              Pending Requests ({pendingRequests.length})
            </Button>
            <Button
              size="sm"
              variant={filterStatus === "all" ? "secondary" : "ghost"}
              className="h-8 text-xs font-semibold"
              onClick={() => setFilterStatus("all")}
            >
              All ({mcpRequests.length})
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-8 text-center text-xs text-muted-foreground">
            Loading developer access grants…
          </div>
        ) : filteredGrants.length === 0 ? (
          <div className="p-10 text-center text-muted-foreground">
            <Users className="h-8 w-8 mx-auto opacity-30 mb-2" />
            <p className="text-sm font-semibold text-foreground">No access grants match criteria</p>
            <p className="text-xs mt-0.5">
              Approved MCP tool requests submitted from the Developer Portal will appear here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-muted/40 border-b border-border text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Requester / User</th>
                  <th className="px-4 py-3">Target MCP Server</th>
                  <th className="px-4 py-3">Granted Operations</th>
                  <th className="px-4 py-3">Decision &amp; Governance</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {filteredGrants.map((grant: ApiApprovalRequest) => {
                  const serverName = grant.requested_mcp_tool || grant.tool || grant.resource || "MCP Server";
                  const operations = grant.requested_mcp_tools && grant.requested_mcp_tools.length > 0
                    ? grant.requested_mcp_tools
                    : ["All Server Tools"];
                  const isPending = grant.status === "pending";
                  const isApproved = grant.status === "approved";

                  return (
                    <tr key={grant.id} className="hover:bg-muted/30 transition-colors">
                      {/* User Column */}
                      <td className="px-5 py-3.5 align-top">
                        <div className="font-semibold text-foreground flex items-center gap-1.5">
                          <span className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-[11px]">
                            {(grant.user_name || "U")[0].toUpperCase()}
                          </span>
                          <span>{grant.user_name || "Developer"}</span>
                        </div>
                        <p className="text-[11px] text-muted-foreground mt-0.5 font-mono">
                          ID: {grant.id.substring(0, 8)}
                        </p>
                      </td>

                      {/* Server Column */}
                      <td className="px-4 py-3.5 align-top">
                        <div className="flex items-center gap-1.5">
                          <Server className="w-3.5 h-3.5 text-primary shrink-0" />
                          <span className="font-bold text-foreground text-xs">{serverName}</span>
                        </div>
                        {grant.reason && (
                          <p className="text-[11px] text-muted-foreground mt-1 line-clamp-1 italic max-w-xs">
                            "{grant.reason}"
                          </p>
                        )}
                      </td>

                      {/* Operations Chips */}
                      <td className="px-4 py-3.5 align-top">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {operations.map((op: string) => (
                            <span 
                              key={op} 
                              className="font-mono text-[10px] bg-background border border-border/80 px-2 py-0.5 rounded-md font-medium text-foreground"
                            >
                              {op}
                            </span>
                          ))}
                        </div>
                      </td>

                      {/* Decision Details */}
                      <td className="px-4 py-3.5 align-top text-muted-foreground">
                        {isApproved ? (
                          <>
                            <p className="font-medium text-foreground">
                              Approved by <span className="text-primary font-bold">{grant.decided_by || "Admin"}</span>
                            </p>
                            {grant.decided_at && (
                              <p className="text-[11px] mt-0.5">
                                {new Date(grant.decided_at).toLocaleDateString()}
                              </p>
                            )}
                          </>
                        ) : isPending ? (
                          <span className="text-amber-600 dark:text-amber-400 font-medium">
                            Awaiting sign-off
                          </span>
                        ) : (
                          <span className="text-rose-600 dark:text-rose-400 font-medium">
                            Rejected by {grant.decided_by || "Admin"}
                          </span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3.5 align-top">
                        <Badge variant={isApproved ? "success" : isPending ? "warning" : "destructive"}>
                          {isApproved ? "Active Grant" : isPending ? "Pending Review" : "Revoked"}
                        </Badge>
                      </td>

                      {/* Actions */}
                      <td className="px-5 py-3.5 align-top text-right">
                        {isApproved && canEdit && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/30 h-7 text-xs font-semibold"
                            disabled={revokeMutation.isPending}
                            onClick={() => revokeMutation.mutate(grant.id)}
                          >
                            <Trash2 className="w-3.5 h-3.5 mr-1" />
                            Revoke
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
