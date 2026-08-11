import type { PolicyTreeNode } from "@/lib/types/domain";

export interface PolicyGraphLink {
  policy_id: string;
  policy_name: string;
  policy_status: string | null;
  graph_node_id: string;
  graph_node_label: string;
  graph_node_type: string;
  edge_labels: string[];
  description: string;
}


export function findPolicyInTree(nodes: PolicyTreeNode[], policyId: string): PolicyTreeNode | null {
  for (const node of nodes) {
    if (node.id === policyId && node.type === "policy") return node;
    if (node.children) {
      const found = findPolicyInTree(node.children, policyId);
      if (found) return found;
    }
  }
  return null;
}

export function findFirstPolicy(nodes: PolicyTreeNode[]): PolicyTreeNode | null {
  for (const node of nodes) {
    if (node.type === "policy") return node;
    if (node.children) {
      const found = findFirstPolicy(node.children);
      if (found) return found;
    }
  }
  return null;
}

export function graphUrlForPolicy(link: Pick<PolicyGraphLink, "policy_id" | "graph_node_id">) {
  return `/governance-graph?node=${encodeURIComponent(link.graph_node_id)}&policy=${encodeURIComponent(link.policy_id)}`;
}

export function policyStudioUrl(policyId: string) {
  return `/policy-studio?policy=${encodeURIComponent(policyId)}`;
}
