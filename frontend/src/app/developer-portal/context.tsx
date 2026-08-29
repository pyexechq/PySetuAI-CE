"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useAuthStore } from '@/stores/auth-store';

export type Environment = 'Development' | 'Staging' | 'Production';

export interface PortalContextType {
  environment: Environment;
  setEnvironment: (env: Environment) => void;
  cart: any[];
  setCart: React.Dispatch<React.SetStateAction<any[]>>;
  isCartOpen: boolean;
  setIsCartOpen: (open: boolean) => void;
  provisionedTools: any[];
  setProvisionedTools: React.Dispatch<React.SetStateAction<any[]>>;
  requestedTools: any[];
  setRequestedTools: React.Dispatch<React.SetStateAction<any[]>>;
  apiKeys: any[];
  setApiKeys: React.Dispatch<React.SetStateAction<any[]>>;
  catalogItems: any[];
  loading: boolean;
  portalEnabled: boolean;
  refreshData: () => Promise<void>;
}

const PortalContext = createContext<PortalContextType | undefined>(undefined);

// Default pre-approved / auto-provisioned standard tools
const DEFAULT_SYSTEM_TOOLS = [
  {
    id: 'mcp-fs-01',
    name: 'Local FileSystem MCP',
    category: 'Development',
    description: 'Provides secure read/write access to specific local directories for your AI agents.',
    version: '1.2.0',
    status: 'Available',
    requiresApproval: false,
    features: ['Read-only mode', 'Path restrictions', 'MIME type filtering'],
    selectedFunctions: ['fs-read_file', 'fs-list_dir'],
    discoveredTools: [
      { id: 'fs-read_file', name: 'read_file', description: 'Read file contents.' },
      { id: 'fs-list_dir', name: 'list_directory', description: 'List files in directory.' },
    ],
    serverConfig: { command: "npx", args: ["-y", "@modelcontextprotocol/server-filesystem", "/secure/data"], env: {} },
  },
  {
    id: 'mcp-ai-01',
    name: 'AI Gateway Model Router',
    category: 'AI',
    description: 'Direct access to company-sanctioned LLM models with built-in PII and prompt-injection guardrails.',
    version: '3.0.0',
    status: 'Available',
    requiresApproval: false,
    features: ['Prompt routing', 'Model fallback', 'Token tracking'],
    selectedFunctions: [],
    discoveredTools: [],
    serverConfig: null,
  }
];

export function PortalProvider({ children }: { children: ReactNode }) {
  const { token, user, isAuthenticated } = useAuthStore();
  const [environment, setEnvironment] = useState<Environment>('Development');
  const [cart, setCart] = useState<any[]>([]);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [provisionedTools, setProvisionedTools] = useState<any[]>(DEFAULT_SYSTEM_TOOLS);
  const [requestedTools, setRequestedTools] = useState<any[]>([]);
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [catalogItems, setCatalogItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [portalEnabled, setPortalEnabled] = useState(true);

  const refreshData = useCallback(async () => {
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      // 0. Check Tenant Portal Enablement
      try {
        const settingsRes = await fetch("/api/v1/mcp/portal/settings", { headers });
        if (settingsRes.ok) {
          const settingsData = await settingsRes.json();
          if (settingsData.enabled === false && user?.role !== "platform_admin") {
            setPortalEnabled(false);
            setLoading(false);
            return;
          } else {
            setPortalEnabled(true);
          }
        }
      } catch {
        setPortalEnabled(true);
      }

      // 1. Fetch live Client API keys
      const keysRes = await fetch("/api/v1/client-api-keys", { headers });
      if (keysRes.ok) {
        const keysData = await keysRes.json();
        const mappedKeys = keysData.map((k: any) => ({
          id: k.id,
          name: k.name,
          description: k.description || '',
          value: k.key_masked || (k.key_prefix ? `${k.key_prefix}...` : 'ps-live-••••••••'),
          maskedKey: k.key_masked || (k.key_prefix ? `${k.key_prefix}...` : 'ps-live-••••••••'),
          keyPrefix: k.key_prefix,
          revealable: Boolean(k.revealable),
          createdAt: k.created_at ? new Date(k.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Active',
          environment: environment,
          bundleName: k.bundle_name || 'Default Governance',
          model: { name: k.bundle_name || 'PySetu Default Bundle', provider: 'PySetu AI Gateway' },
          attachedTools: DEFAULT_SYSTEM_TOOLS,
          rateLimits: {
            rpm: k.ai_rate_limit_rpm,
            rph: k.ai_rate_limit_rph,
            rpd: k.ai_rate_limit_rpd,
            tpm: k.ai_token_limit_tpm,
          },
          isActive: k.is_active,
        }));
        setApiKeys(mappedKeys);
      }

      // 2. Fetch live Approvals (status=all)
      const approvalsRes = await fetch("/api/v1/approvals?status=all", { headers });
      if (approvalsRes.ok) {
        const approvalsData = await approvalsRes.json();
        const mappedRequests = approvalsData.map((req: any) => {
          const reqStatus = (req.status || '').toLowerCase();
          const normalizedStatus = reqStatus === 'approved' ? 'Approved' : reqStatus === 'rejected' ? 'Rejected' : 'Pending Review';
          const tName = req.requested_mcp_tool || req.tool || req.policy_name || 'Resource Access';
          return {
            requestId: req.id ? `REQ-${req.id.toString().substring(0, 8).toUpperCase()}` : 'REQ-LIVE',
            rawId: req.id,
            toolId: req.requested_mcp_tool || req.tool || (req.requested_mcp_tools?.[0]) || req.resource,
            toolName: tName,
            action: req.action || 'mcp_access_request',
            reason: req.reason,
            status: normalizedStatus,
            submittedAt: req.created_at ? new Date(req.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Recently',
            decidedBy: req.decided_by || null,
            decidedAt: req.decided_at ? new Date(req.decided_at).toLocaleDateString() : null,
            selectedFunctions: req.requested_mcp_tools || [],
          };
        });
        setRequestedTools(mappedRequests);

        // Dynamically compute provisioned tools from approved requests + defaults
        const dynamicProvisioned = [...DEFAULT_SYSTEM_TOOLS];
        mappedRequests.forEach((req: any) => {
          if (req.status === 'Approved') {
            if (!dynamicProvisioned.some(p => p.name.toLowerCase() === req.toolName.toLowerCase())) {
              dynamicProvisioned.push({
                id: req.toolId || `tool-${req.rawId}`,
                name: req.toolName,
                category: 'Approved Integration',
                description: req.reason ? `Access granted: ${req.reason}` : `Access granted via approved request ${req.requestId}.`,
                version: '1.0.0',
                status: 'Provisioned',
                requiresApproval: false,
                features: ['Access Granted', 'Full Policy Audit', ...(req.selectedFunctions || [])],
                selectedFunctions: req.selectedFunctions,
                discoveredTools: req.selectedFunctions || [],
                serverConfig: null,
              });
            }
          }
        });
        setProvisionedTools(dynamicProvisioned);
      }

      // 3. Fetch Catalog
      const catalogRes = await fetch("/api/v1/mcp/portal/catalog", { headers });
      if (catalogRes.ok) {
        const catData = await catalogRes.json();
        const bundles = (catData.bundles || []).map((b: any) => ({ ...b, isBundle: true, status: 'Available' }));
        const tools = (catData.tools || []).map((t: any) => ({ ...t, isBundle: false, status: 'Available' }));
        setCatalogItems([...bundles, ...tools]);
      }
    } catch (err) {
      console.error("PortalContext refreshData error:", err);
    } finally {
      setLoading(false);
    }
  }, [token, environment]);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  return (
    <PortalContext.Provider value={{
      environment, setEnvironment,
      cart, setCart,
      isCartOpen, setIsCartOpen,
      provisionedTools, setProvisionedTools,
      requestedTools, setRequestedTools,
      apiKeys, setApiKeys,
      catalogItems,
      loading,
      portalEnabled,
      refreshData
    }}>
      {children}
    </PortalContext.Provider>
  );
}

export function usePortalContext() {
  const context = useContext(PortalContext);
  if (!context) {
    throw new Error('usePortalContext must be used within a PortalProvider');
  }
  return context;
}
