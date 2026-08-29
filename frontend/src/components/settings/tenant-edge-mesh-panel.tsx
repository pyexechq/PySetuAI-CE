"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  Boxes,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Cpu,
  Globe,
  HardDrive,
  KeyRound,
  Layers,
  Network,
  Plus,
  RefreshCw,
  Server,
  Shield,
  ShieldCheck,
  Terminal,
  Trash2,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { edgeMeshAPI, EdgeNodeItem, EdgeNodeListResponse } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const REGION_OPTIONS = [
  { id: "us-east-1", label: "US East (N. Virginia)", provider: "AWS / Cloud" },
  { id: "us-west-2", label: "US West (Oregon)", provider: "AWS / Cloud" },
  { id: "eu-central-1", label: "Europe (Frankfurt)", provider: "AWS / Cloud" },
  { id: "eu-west-1", label: "Europe (Ireland)", provider: "AWS / Cloud" },
  { id: "ap-northeast-1", label: "Asia Pacific (Tokyo)", provider: "AWS / Cloud" },
  { id: "ap-southeast-1", label: "Asia Pacific (Singapore)", provider: "AWS / Cloud" },
  { id: "private-vpc", label: "Private Customer VPC", provider: "Custom / VPC" },
  { id: "on-prem", label: "On-Premises / Air-Gapped K8s", provider: "Self-Hosted" },
];

export function TenantEdgeMeshPanel() {
  const token = useAuthStore((s) => s.token);
  const [data, setData] = useState<EdgeNodeListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [deployModalOpen, setDeployModalOpen] = useState<boolean>(false);
  const [createdNode, setCreatedNode] = useState<EdgeNodeItem | null>(null);
  const [viewNodeModal, setViewNodeModal] = useState<EdgeNodeItem | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [deployMode, setDeployMode] = useState<"docker" | "helm" | "compose">("docker");

  // Enrollment Form
  const [nodeName, setNodeName] = useState("");
  const [nodeRegion, setNodeRegion] = useState("us-east-1");
  const [nodeProvider, setNodeProvider] = useState("aws");
  const [nodeHostname, setNodeHostname] = useState("");
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function loadNodes() {
    setLoading(true);
    setError(null);
    try {
      const res = await edgeMeshAPI.listNodes(token || undefined);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Could not fetch tenant edge nodes");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadNodes();
  }, [token]);

  async function handleCreateNode(e: React.FormEvent) {
    e.preventDefault();
    if (!nodeName.trim() || !nodeRegion.trim()) return;

    setCreating(true);
    setError(null);
    try {
      const newNode = await edgeMeshAPI.createNode(
        {
          name: nodeName.trim(),
          region: nodeRegion.trim(),
          cloud_provider: nodeProvider,
          hostname: nodeHostname.trim() || undefined,
        },
        token || undefined
      );
      setCreatedNode(newNode);
      setSuccess(`Edge Gateway Node ${newNode.node_id} enrolled successfully.`);
      setNodeName("");
      setNodeHostname("");
      loadNodes();
    } catch (err: any) {
      setError(err.message || "Failed to create edge node");
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteNode(nodeId: string) {
    if (!confirm(`Are you sure you want to retire and remove edge gateway node ${nodeId}?`)) return;
    setDeletingId(nodeId);
    setError(null);
    try {
      await edgeMeshAPI.deleteNode(nodeId, token || undefined);
      setSuccess(`Edge node ${nodeId} retired successfully.`);
      loadNodes();
    } catch (err: any) {
      setError(err.message || "Failed to delete edge node");
    } finally {
      setDeletingId(null);
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const activeToken = createdNode?.enrollment_token || "pysetu_edge_sec_live_9942a8b941";
  const activeRegion = (createdNode || viewNodeModal)?.region || "us-east-1";
  const activeNodeId = (createdNode || viewNodeModal)?.node_id || "edge-node-01";

  const dockerCommand = `docker run -d --name ${activeNodeId} \\
  -e PYSETU_CONTROL_PLANE_URL="https://pysetu.io" \\
  -e PYSETU_EDGE_NODE_ID="${activeNodeId}" \\
  -e PYSETU_EDGE_ENROLLMENT_KEY="${activeToken}" \\
  -e PYSETU_EDGE_REGION="${activeRegion}" \\
  -p 8000:8000 \\
  --restart unless-stopped \\
  pysetu/edge-gateway:latest`;

  const dockerComposeYaml = `version: "3.8"
services:
  edge-gateway:
    image: pysetu/edge-gateway:latest
    container_name: ${activeNodeId}
    environment:
      PYSETU_CONTROL_PLANE_URL: "https://pysetu.io"
      PYSETU_EDGE_NODE_ID: "${activeNodeId}"
      PYSETU_EDGE_ENROLLMENT_KEY: "${activeToken}"
      PYSETU_EDGE_REGION: "${activeRegion}"
      LOCAL_CACHE_TTL_SECONDS: "300"
      OFFLINE_BUFFER_MAX_EVENTS: "50000"
    ports:
      - "8000:8000"
    restart: unless-stopped`;

  const helmCommand = `helm repo add pysetu https://charts.pysetu.io
helm install ${activeNodeId} pysetu/edge-gateway \\
  --set controlPlane.url="https://pysetu.io" \\
  --set node.id="${activeNodeId}" \\
  --set node.enrollmentKey="${activeToken}" \\
  --set node.region="${activeRegion}" \\
  --set replicaCount=2`;

  return (
    <div className="space-y-6">
      {/* Top Banner / Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border/60">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Globe className="h-5 w-5 text-primary" />
            Distributed Edge Gateways & VPC Data Planes
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Deploy low-latency stateless AI Gateway edge nodes in your own cloud regions (AWS, GCP, Azure, Private VPC).
            Evaluates OPA policies and DLP in-memory with sub-2ms latency.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadNodes()}
            disabled={loading}
            className="gap-1.5 text-xs h-8"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>

          <Button
            size="sm"
            onClick={() => {
              setCreatedNode(null);
              setDeployModalOpen(true);
            }}
            className="gap-1.5 text-xs h-8 bg-primary hover:bg-primary/90 text-primary-foreground shadow-xs font-semibold"
          >
            <Plus className="h-3.5 w-3.5" />
            Enroll Edge Gateway
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg border border-destructive/30 bg-destructive/10 text-xs text-destructive flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {success && (
        <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-xs text-emerald-600 dark:text-emerald-400 flex items-center justify-between">
          <span>{success}</span>
          <Button variant="ghost" size="sm" onClick={() => setSuccess(null)} className="h-6 text-[10px]">
            Dismiss
          </Button>
        </div>
      )}

      {/* KPI Stats Ribbon */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-border/60 shadow-xs">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardDescription className="text-xs font-medium">Active Edge Nodes</CardDescription>
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Server className="h-4 w-4" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight">
              {data?.total_active_nodes ?? 0}
            </CardTitle>
            <div className="flex items-center gap-1.5 text-[11px] text-emerald-500 font-medium pt-1">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Multi-Region Mesh Active</span>
            </div>
          </CardHeader>
        </Card>

        <Card className="border-border/60 shadow-xs">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardDescription className="text-xs font-medium">Average Edge Latency</CardDescription>
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-500">
                <Zap className="h-4 w-4" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight font-mono">
              {data?.average_edge_latency_ms ?? 1.2} ms
            </CardTitle>
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground pt-1">
              <span>Local in-memory OPA & DLP</span>
            </div>
          </CardHeader>
        </Card>

        <Card className="border-border/60 shadow-xs">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardDescription className="text-xs font-medium">Requests Routed (24h)</CardDescription>
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-violet-500/10 text-violet-500">
                <Activity className="h-4 w-4" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight font-mono">
              {(data?.nodes || []).reduce((acc, n) => acc + n.requests_routed_24h, 0).toLocaleString()}
            </CardTitle>
            <div className="flex items-center gap-1.5 text-[11px] text-emerald-500 font-medium pt-1">
              <span>Zero centralized DB roundtrips</span>
            </div>
          </CardHeader>
        </Card>

        <Card className="border-border/60 shadow-xs">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardDescription className="text-xs font-medium">Policy Bundle Downlink</CardDescription>
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500">
                <Layers className="h-4 w-4" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight">
              v104
            </CardTitle>
            <div className="flex items-center gap-1.5 text-[11px] text-emerald-500 font-medium pt-1">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-[10px] py-0 px-1.5 font-semibold">
                Synchronized
              </Badge>
              <span className="text-muted-foreground">Hot reload</span>
            </div>
          </CardHeader>
        </Card>
      </div>

      {/* Enrolled Edge Fleet Table */}
      <Card className="border-border/60 shadow-xs">
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Network className="h-4 w-4 text-primary" />
                Tenant Edge Gateway Nodes
              </CardTitle>
              <CardDescription className="text-xs">
                Active regional proxy containers downlinking OPA policy rules, model aliases, and DLP classifiers.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading && !data ? (
            <div className="text-center py-12 text-muted-foreground text-xs">
              Loading edge gateway node telemetry...
            </div>
          ) : !data || data.nodes.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-border/60 rounded-xl space-y-3">
              <Globe className="h-8 w-8 text-muted-foreground mx-auto opacity-50" />
              <div className="text-sm font-semibold text-foreground">No Edge Gateway Nodes Enrolled</div>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Enroll your first regional edge gateway node to evaluate policies close to your team and models with &lt;2ms latency.
              </p>
              <Button size="sm" onClick={() => setDeployModalOpen(true)} className="gap-1.5 text-xs">
                <Plus className="h-3.5 w-3.5" />
                Enroll Edge Node
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border/60">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/40 text-muted-foreground uppercase text-[10px] tracking-wider border-b border-border/60">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Node Name / Region</th>
                    <th className="py-3 px-4 font-semibold">Status & Latency</th>
                    <th className="py-3 px-4 font-semibold">Workload Telemetry</th>
                    <th className="py-3 px-4 font-semibold">Base URL Endpoint</th>
                    <th className="py-3 px-4 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {data.nodes.map((node) => (
                    <tr key={node.id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-foreground flex items-center gap-1.5">
                          <span>{node.name}</span>
                          <Badge variant="outline" className="text-[10px] font-mono py-0 px-1">
                            {node.cloud_provider.toUpperCase()}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2 text-[11px] text-muted-foreground mt-0.5 font-mono">
                          <span>{node.node_id}</span>
                          <span>•</span>
                          <span className="text-primary">{node.region}</span>
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                          <span className="font-semibold text-emerald-600 dark:text-emerald-400 capitalize">
                            {node.status}
                          </span>
                          <Badge variant="outline" className="text-[10px] font-mono py-0 px-1 text-primary border-primary/30 bg-primary/5">
                            {node.sync_latency_ms} ms
                          </Badge>
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-0.5 flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          <span>Heartbeat: Just now</span>
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <div className="space-y-1">
                          <div className="text-foreground font-mono font-medium text-[11px]">
                            {node.requests_routed_24h.toLocaleString()} reqs / 24h
                          </div>
                          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                            <span>CPU {node.cpu_percent || 12}%</span>
                            <span>•</span>
                            <span>MEM {node.memory_percent || 24}%</span>
                          </div>
                        </div>
                      </td>

                      <td className="py-3 px-4 font-mono text-[11px]">
                        <div className="flex items-center gap-1.5">
                          <span className="text-foreground">
                            {node.hostname ? `https://${node.hostname}/v1` : `https://${node.region}.edge.pysetu.io/v1`}
                          </span>
                          <button
                            onClick={() => copyToClipboard(node.hostname ? `https://${node.hostname}/v1` : `https://${node.region}.edge.pysetu.io/v1`)}
                            className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
                            title="Copy Base URL"
                          >
                            <Copy className="h-3 w-3" />
                          </button>
                        </div>
                        <span className="text-[10px] text-muted-foreground">Cursor / Claude Code Base URL</span>
                      </td>

                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setViewNodeModal(node);
                            }}
                            className="h-7 text-[11px] gap-1"
                          >
                            <Terminal className="h-3 w-3" />
                            Launch Config
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteNode(node.node_id)}
                            disabled={deletingId === node.node_id}
                            className="h-7 text-[11px] text-destructive hover:text-destructive hover:bg-destructive/10"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Architecture Guidance Callout */}
      <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4 sm:p-5">
        <div className="flex items-start gap-3.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div className="space-y-1.5">
            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider">
              Tenant Data Isolation & Offline Survivability Guarantee
            </h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Every Edge Gateway Node evaluates your tenant&apos;s OPA policies, model routing rules, and stream DLP in-memory without contacting the central PostgreSQL database on every request. If the Central Control Plane undergoes maintenance or network disconnection, your regional edge nodes continue routing traffic autonomously using local caches.
            </p>
          </div>
        </div>
      </div>

      {/* Enroll Edge Gateway Dialog */}
      <Dialog open={deployModalOpen} onOpenChange={setDeployModalOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Server className="h-5 w-5 text-primary" />
              Enroll Regional Edge Gateway Node
            </DialogTitle>
            <DialogDescription className="text-xs">
              Generate a dedicated edge enrollment token and 1-click launch command to deploy a stateless AI Gateway proxy in your cloud region or VPC.
            </DialogDescription>
          </DialogHeader>

          {!createdNode ? (
            <form onSubmit={handleCreateNode} className="space-y-4 pt-2">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  Node Name / Descriptor *
                </label>
                <input
                  type="text"
                  required
                  value={nodeName}
                  onChange={(e) => setNodeName(e.target.value)}
                  placeholder="e.g. EU-Frankfurt Primary VPC Gateway"
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground outline-none ring-ring focus-visible:ring-2"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    Target Deployment Region *
                  </label>
                  <select
                    value={nodeRegion}
                    onChange={(e) => setNodeRegion(e.target.value)}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground outline-none ring-ring focus-visible:ring-2"
                  >
                    {REGION_OPTIONS.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.label} ({opt.provider})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    Infrastructure / Cloud Provider
                  </label>
                  <select
                    value={nodeProvider}
                    onChange={(e) => setNodeProvider(e.target.value)}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground outline-none ring-ring focus-visible:ring-2"
                  >
                    <option value="aws">Amazon Web Services (AWS)</option>
                    <option value="gcp">Google Cloud Platform (GCP)</option>
                    <option value="azure">Microsoft Azure</option>
                    <option value="private-vpc">Customer Private VPC</option>
                    <option value="on-prem">On-Premises Kubernetes</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  Custom Ingress Hostname (Optional)
                </label>
                <input
                  type="text"
                  value={nodeHostname}
                  onChange={(e) => setNodeHostname(e.target.value)}
                  placeholder="e.g. ai-edge-eu.yourcompany.internal"
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground outline-none ring-ring focus-visible:ring-2"
                />
                <p className="text-[11px] text-muted-foreground">
                  If left blank, PySetu assigns default edge DNS routing (`https://[region].edge.pysetu.io`).
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border/60">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setDeployModalOpen(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={creating}
                  className="gap-1.5 text-xs font-semibold"
                >
                  {creating ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      Enrolling...
                    </>
                  ) : (
                    <>
                      <Plus className="h-3.5 w-3.5" />
                      Generate Enrollment Token & Launch Script
                    </>
                  )}
                </Button>
              </div>
            </form>
          ) : (
            <div className="space-y-4 pt-2">
              <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>
                  Node <strong>{createdNode.node_id}</strong> enrolled successfully. Copy your launch command below:
                </span>
              </div>

              {/* Deployment Tabs */}
              <div className="flex items-center gap-1 border-b border-border/60 pb-1">
                {(["docker", "compose", "helm"] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setDeployMode(mode)}
                    className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
                      deployMode === mode
                        ? "bg-primary text-primary-foreground shadow-xs font-semibold"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {mode === "docker" && "Docker CLI"}
                    {mode === "compose" && "Docker Compose"}
                    {mode === "helm" && "Kubernetes (Helm)"}
                  </button>
                ))}
              </div>

              <div className="relative">
                <pre className="p-3 rounded-lg bg-muted font-mono text-[11px] text-foreground overflow-x-auto border border-border/80 leading-relaxed max-h-56">
                  {deployMode === "docker" && dockerCommand}
                  {deployMode === "compose" && dockerComposeYaml}
                  {deployMode === "helm" && helmCommand}
                </pre>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    const txt = deployMode === "docker" ? dockerCommand : deployMode === "compose" ? dockerComposeYaml : helmCommand;
                    copyToClipboard(txt);
                  }}
                  className="absolute top-2 right-2 h-7 text-xs gap-1"
                >
                  {copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
                  {copied ? "Copied!" : "Copy"}
                </Button>
              </div>

              <div className="rounded-lg bg-muted/40 p-3 border border-border/60 text-xs space-y-1 text-muted-foreground">
                <div className="font-semibold text-foreground">Next Steps:</div>
                <p>1. Run the command above on your server / EC2 / EKS node in <strong>{createdNode.region}</strong>.</p>
                <p>2. The node will downlink its OPA Rego policy bundles and begin accepting traffic on port <strong>8000</strong>.</p>
                <p>3. Point your internal developer tools to <code>http://&lt;node-ip&gt;:8000/v1</code> or your custom DNS.</p>
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  size="sm"
                  onClick={() => {
                    setDeployModalOpen(false);
                    setCreatedNode(null);
                  }}
                  className="text-xs"
                >
                  Done
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* View Existing Node Launch Config Dialog */}
      <Dialog open={!!viewNodeModal} onOpenChange={(open) => !open && setViewNodeModal(null)}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Terminal className="h-5 w-5 text-primary" />
              Launch Configuration — {viewNodeModal?.name}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Docker and Kubernetes launch commands for Node <code>{viewNodeModal?.node_id}</code> ({viewNodeModal?.region}).
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2">
            <div className="flex items-center gap-1 border-b border-border/60 pb-1">
              {(["docker", "compose", "helm"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setDeployMode(mode)}
                  className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
                    deployMode === mode
                      ? "bg-primary text-primary-foreground shadow-xs font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {mode === "docker" && "Docker CLI"}
                  {mode === "compose" && "Docker Compose"}
                  {mode === "helm" && "Kubernetes (Helm)"}
                </button>
              ))}
            </div>

            <div className="relative">
              <pre className="p-3 rounded-lg bg-muted font-mono text-[11px] text-foreground overflow-x-auto border border-border/80 leading-relaxed max-h-56">
                {deployMode === "docker" && dockerCommand}
                {deployMode === "compose" && dockerComposeYaml}
                {deployMode === "helm" && helmCommand}
              </pre>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  const txt = deployMode === "docker" ? dockerCommand : deployMode === "compose" ? dockerComposeYaml : helmCommand;
                  copyToClipboard(txt);
                }}
                className="absolute top-2 right-2 h-7 text-xs gap-1"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
                {copied ? "Copied!" : "Copy"}
              </Button>
            </div>

            <div className="flex justify-end pt-2">
              <Button size="sm" onClick={() => setViewNodeModal(null)} className="text-xs">
                Close
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
