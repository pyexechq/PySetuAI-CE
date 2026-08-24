"use client";

import { useState, useEffect } from 'react';
import {
  Search, Database, Globe, Shield, Key, Package, Cpu,
  Check, X, Copy, Download, ChevronRight, ChevronDown, Braces, Sparkles,
  Server, Wrench, Layers, Users, DollarSign, Briefcase, ShoppingCart
} from 'lucide-react';
import { Badge } from '@/components/developer-portal/Badge';
import { Button } from '@/components/developer-portal/Button';
import { usePortalContext } from '../context';

const CATEGORIES = [
  "All",
  "Engineering",
  "Productivity",
  "Sales",
  "Human Resources",
  "Finance",
  "Development",
  "Database",
  "Security",
  "AI",
  "Cloud"
];

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  Engineering:      <Cpu className="w-5 h-5 text-indigo-600" />,
  Productivity:     <Wrench className="w-5 h-5 text-blue-600" />,
  Sales:            <ShoppingCart className="w-5 h-5 text-emerald-600" />,
  "Human Resources":<Users className="w-5 h-5 text-purple-600" />,
  Finance:          <DollarSign className="w-5 h-5 text-amber-600" />,
  Development:      <Server className="w-5 h-5 text-cyan-600" />,
  Database:         <Database className="w-5 h-5 text-blue-600" />,
  Security:         <Shield className="w-5 h-5 text-rose-600" />,
  AI:               <Sparkles className="w-5 h-5 text-violet-600" />,
  Cloud:            <Globe className="w-5 h-5 text-teal-600" />,
};

export default function CataloguePage() {
  const { provisionedTools, requestedTools, cart, setCart, setIsCartOpen } = usePortalContext();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');
  const [selectedTool, setSelectedTool] = useState<any>(null);
  const [selectedFunctions, setSelectedFunctions] = useState<string[]>([]);
  const [serverConfigOpen, setServerConfigOpen] = useState(false);
  const [configCopied, setConfigCopied] = useState(false);
  const [modalSearch, setModalSearch] = useState('');

  const [allItems, setAllItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCatalog() {
      try {
        const res = await fetch("/api/v1/mcp/portal/catalog");
        if (res.ok) {
          const data = await res.json();
          const serverList = (data.servers || []).map((s: any) => {
            const toolNames = s.tool_names || [];
            const discoveredTools = toolNames.map((name: string) => ({
              id: name,
              name: name,
              description: `Tool operation exposed by ${s.name}`,
            }));

            return {
              id: s.id,
              name: s.name,
              category: s.category || 'Development',
              status: s.status || 'Available',
              transport: s.transport || 'sse',
              endpointUrl: s.endpoint_url,
              toolsCount: s.tools_count || toolNames.length,
              toolNames: toolNames,
              description: s.description || `Published MCP Server for ${s.name} operations.`,
              features: s.features?.length > 0 ? s.features : [
                'Live MCP Protocol',
                `${toolNames.length || s.tools_count || 1} Tools`,
                'Policy-Governed',
              ],
              requiresApproval: s.requires_approval !== false,
              discoveredTools: discoveredTools,
              serverConfig: s.server_config || {
                transport: s.transport || 'sse',
                url: s.endpoint_url || `http://mcp-gateway:8000/mcp/${s.id}`,
              },
            };
          });
          setAllItems(serverList);
        }
      } catch (err) {
        console.error("Failed to fetch catalog", err);
      } finally {
        setLoading(false);
      }
    }
    fetchCatalog();
  }, []);

  useEffect(() => {
    if (selectedTool) {
      setServerConfigOpen(false);
      setModalSearch('');
      const existing = provisionedTools.find((t: any) => t.id === selectedTool.id);
      if (existing?.selectedFunctions?.length > 0) {
        setSelectedFunctions(existing.selectedFunctions);
      } else if (selectedTool.discoveredTools?.length > 0) {
        setSelectedFunctions(selectedTool.discoveredTools.map((fn: any) => fn.id));
      } else {
        setSelectedFunctions([]);
      }
    }
  }, [selectedTool, provisionedTools]);

  const filteredTools = allItems.filter(t => {
    const matchesSearch =
      t.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.category?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.toolNames && t.toolNames.some((tn: string) => tn.toLowerCase().includes(searchQuery.toLowerCase())));
    const matchesCategory = activeCategory === 'All' || t.category === activeCategory;
    return matchesSearch && matchesCategory;
  });

  const isProvisioned = (tool: any) => {
    if (!tool) return false;
    return provisionedTools.some((t: any) => 
      t.id === tool.id || (tool.name && t.name?.toLowerCase() === tool.name.toLowerCase())
    );
  };

  const isRequested = (tool: any) => {
    if (!tool) return false;
    return requestedTools.some((req: any) => 
      req.status === 'Pending Review' && 
      (req.toolId === tool.id || (tool.name && req.toolName?.toLowerCase() === tool.name.toLowerCase()))
    );
  };

  const isInCart = (toolId: string) => cart.some((t: any) => t.id === toolId);

  const handleModalAction = () => {
    if (!selectedTool) return;
    const cartItem = { ...selectedTool, selectedFunctions };
    setCart((prev: any[]) => [...prev, cartItem]);
    setSelectedTool(null);
    setIsCartOpen(true);
  };

  const handleCopyConfig = (text: string) => {
    navigator.clipboard.writeText(text);
    setConfigCopied(true);
    setTimeout(() => setConfigCopied(false), 2000);
  };

  const getConfigJson = (tool: any) => {
    if (!tool?.serverConfig) return null;
    const key = tool.name.replace(/\s+/g, '-').toLowerCase();
    return JSON.stringify({ mcpServers: { [key]: tool.serverConfig } }, null, 2);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">Tool &amp; Resource Catalogue</h1>
          <p className="text-sm font-medium text-slate-500 mt-1">Discover and request published MCP Servers for your agents.</p>
        </div>
        <div className="relative w-full sm:w-80">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-slate-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-4 py-2 border border-slate-200 rounded-xl bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm shadow-xs"
            placeholder="Search published MCP servers, tools..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Category Filter Pills */}
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-2 px-2 sm:mx-0 sm:px-0">
        {CATEGORIES.map(category => {
          const isActive = activeCategory === category;
          return (
            <button
              key={category}
              onClick={() => setActiveCategory(category)}
              className={`px-4 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-white border border-slate-200/80 text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              {category}
            </button>
          );
        })}
      </div>

      {/* Tool Grid */}
      {loading ? (
        <div className="text-center py-20 text-slate-500">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          Loading published MCP servers...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTools.map(tool => {
            const provisioned = isProvisioned(tool);
            const requested = isRequested(tool);
            const inCart = isInCart(tool.id);
            const icon = CATEGORY_ICONS[tool.category] || <Server className="w-5 h-5 text-slate-500" />;

            return (
              <div key={tool.id} className="bg-white rounded-2xl border border-slate-200/80 p-6 flex flex-col justify-between shadow-[0_4px_20px_-4px_rgba(0,0,0,0.03)] hover:shadow-lg hover:border-indigo-300 transition-all duration-200 group">
                <div>
                  {/* Icon + Status */}
                  <div className="flex justify-between items-start mb-4">
                    <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100 group-hover:scale-105 transition-transform shadow-xs">
                      {icon}
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                        {tool.status}
                      </span>
                      {tool.requiresApproval === false ? (
                        <span className="text-[9px] font-extrabold px-1.5 py-0.2 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100">
                          Auto-Provision
                        </span>
                      ) : (
                        <span className="text-[9px] font-bold px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-600">
                          Requires Approval
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Name + Category + Transport */}
                  <h3 className="text-base font-bold text-slate-900 mb-1">{tool.name}</h3>
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                      {tool.category}
                    </span>
                    <span className="text-[10px] font-mono font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md uppercase">
                      {tool.transport}
                    </span>
                    <span className="text-xs text-slate-400 font-medium">
                      {tool.toolsCount} {tool.toolsCount === 1 ? 'tool' : 'tools'}
                    </span>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">{tool.description}</p>

                  {/* Exposed Tools / Feature Tags */}
                  {tool.toolNames && tool.toolNames.length > 0 ? (
                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {tool.toolNames.slice(0, 3).map((tn: string, i: number) => (
                        <span key={i} className="inline-flex items-center text-[11px] font-mono text-indigo-700 bg-indigo-50/70 px-2.5 py-1 rounded-lg border border-indigo-100 font-medium">
                          <Check className="w-3 h-3 mr-1 text-indigo-500" /> {tn}
                        </span>
                      ))}
                      {tool.toolNames.length > 3 && (
                        <span className="inline-flex items-center text-[11px] font-semibold text-slate-400 bg-slate-50 px-2 py-1 rounded-lg border border-slate-200/60">
                          +{tool.toolNames.length - 3} more
                        </span>
                      )}
                    </div>
                  ) : (
                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {tool.features?.map((feat: string, i: number) => (
                        <span key={i} className="inline-flex items-center text-[11px] font-semibold text-slate-600 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200/60">
                          <Check className="w-3 h-3 mr-1 text-emerald-500" /> {feat}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Action Button */}
                <div className="mt-6">
                  <button
                    onClick={() => setSelectedTool(tool)}
                    disabled={requested || inCart}
                    className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold transition-all shadow-xs ${
                      requested || inCart
                        ? 'bg-slate-100 text-slate-400 border border-slate-200/60 cursor-not-allowed'
                        : provisioned
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-300 hover:bg-emerald-100 active:scale-[0.98]'
                          : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm active:scale-[0.98]'
                    }`}
                  >
                    {provisioned ? '✓ Provisioned · Manage / Update'
                      : requested ? '⏳ Pending Approval'
                      : inCart ? '🛒 In Cart'
                      : 'Configure & Request'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {!loading && filteredTools.length === 0 && (
        <div className="text-center py-20 bg-white border border-slate-200/80 rounded-2xl shadow-xs">
          <Server className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-slate-900">No MCP servers found</h2>
          <p className="text-sm text-slate-500 mt-1">Try adjusting your search or category filters.</p>
        </div>
      )}

      {/* ===== TOOL DETAIL MODAL ===== */}
      {selectedTool && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden border border-slate-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-slate-100 bg-slate-50/50">
              <div className="flex items-center gap-3">
                <div className="bg-white p-2 rounded-xl border border-slate-200 shadow-xs">
                  {CATEGORY_ICONS[selectedTool.category] || <Server className="w-6 h-6 text-indigo-600" />}
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">{selectedTool.name}</h3>
                  <p className="text-xs text-slate-400 font-mono">
                    {selectedTool.id} • {selectedTool.transport?.toUpperCase()}
                  </p>
                </div>
              </div>
              <button onClick={() => setSelectedTool(null)} className="text-slate-400 hover:text-slate-900 p-1.5 rounded-xl hover:bg-slate-100 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              {/* Overview */}
              <div>
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Overview</h4>
                <p className="text-sm text-slate-600 leading-relaxed">{selectedTool.description}</p>
              </div>

              {/* Discovered Functions Selector */}
              {selectedTool.discoveredTools?.length > 0 ? (
                <div>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2">
                      <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                        Available MCP Operations
                      </h4>
                      <span className="font-bold text-indigo-700 bg-indigo-50 border border-indigo-200/60 px-2 py-0.5 rounded-full text-[11px]">
                        {selectedFunctions.length} / {selectedTool.discoveredTools.length} Selected
                      </span>
                    </div>
                    
                    {/* Select All / Deselect All Action Buttons */}
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setSelectedFunctions(selectedTool.discoveredTools.map((fn: any) => fn.id))}
                        className="text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200/80 px-2.5 py-1 rounded-lg transition-colors"
                      >
                        Select All
                      </button>
                      <button
                        type="button"
                        onClick={() => setSelectedFunctions([])}
                        className="text-xs font-bold text-slate-600 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 border border-slate-200 px-2.5 py-1 rounded-lg transition-colors"
                      >
                        Unselect All
                      </button>
                    </div>
                  </div>

                  {/* Operation Quick Filter Search */}
                  {selectedTool.discoveredTools.length > 6 && (
                    <div className="relative mb-2.5">
                      <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
                      <input
                        type="text"
                        placeholder={`Filter operations in ${selectedTool.name}...`}
                        value={modalSearch}
                        onChange={(e) => setModalSearch(e.target.value)}
                        className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:bg-white transition-all"
                      />
                    </div>
                  )}

                  {/* 2-Column Responsive Grid with High Visibility */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-80 overflow-y-auto pr-1">
                    {selectedTool.discoveredTools
                      .filter((fn: any) => 
                        !modalSearch || fn.name.toLowerCase().includes(modalSearch.toLowerCase()) || (fn.description && fn.description.toLowerCase().includes(modalSearch.toLowerCase()))
                      )
                      .map((fn: any) => {
                        const isSelected = selectedFunctions.includes(fn.id);
                        return (
                          <label
                            key={fn.id}
                            className={`flex items-start p-2.5 rounded-xl border transition-all select-none cursor-pointer ${
                              isSelected 
                                ? 'border-indigo-500 bg-indigo-50/50 ring-1 ring-indigo-500' 
                                : 'border-slate-200 bg-white hover:bg-slate-50/80 hover:border-indigo-200'
                            }`}
                          >
                            <input
                              type="checkbox"
                              className="mt-0.5 w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500 cursor-pointer"
                              checked={isSelected}
                              onChange={() => {
                                setSelectedFunctions(prev =>
                                  prev.includes(fn.id) ? prev.filter(id => id !== fn.id) : [...prev, fn.id]
                                );
                              }}
                            />
                            <div className="ml-2.5 min-w-0 flex-1">
                              <span className="font-mono text-xs font-bold text-slate-900 block truncate">
                                {fn.name}
                              </span>
                              <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                                {fn.description}
                              </p>
                            </div>
                          </label>
                        );
                      })}
                  </div>
                </div>
              ) : (
                <div>
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Capabilities</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedTool.features?.map((feat: string, i: number) => (
                      <span key={i} className="inline-flex items-center text-xs font-semibold text-slate-700 bg-emerald-50 border border-emerald-200/60 px-3 py-1 rounded-full">
                        <Check className="w-3.5 h-3.5 mr-1.5 text-emerald-600" /> {feat}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Approval indicator */}
              {selectedTool.requiresApproval !== false && (
                <div className="flex items-center gap-2.5 p-3.5 bg-amber-50 border border-amber-200/80 rounded-xl text-xs text-amber-900 font-medium">
                  <span className="text-amber-500 text-sm">⚠</span>
                  <span>This server <strong>requires admin approval</strong> before tools are provisioned for your agent.</span>
                </div>
              )}
              {selectedTool.requiresApproval === false && (
                <div className="flex items-center gap-2.5 p-3.5 bg-emerald-50 border border-emerald-200/80 rounded-xl text-xs text-emerald-900 font-medium">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>This server will be <strong>instantly provisioned</strong> upon request — no approval needed.</span>
                </div>
              )}

              {/* MCP Server Config */}
              {selectedTool.serverConfig && (
                <div>
                  <button
                    onClick={() => setServerConfigOpen(!serverConfigOpen)}
                    className="w-full flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 group"
                  >
                    <span className="flex items-center gap-1.5 text-slate-700">
                      <Braces className="w-3.5 h-3.5 text-indigo-600" /> MCP Connection Configuration
                    </span>
                    {serverConfigOpen ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                  </button>
                  {serverConfigOpen && (() => {
                    const configJson = getConfigJson(selectedTool)!;
                    return (
                      <div className="border border-slate-200 rounded-xl overflow-hidden shadow-xs">
                        <div className="flex items-center justify-between bg-slate-900 px-4 py-2.5">
                          <span className="text-xs text-slate-400 font-mono">mcp_config.json</span>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleCopyConfig(configJson)}
                              className="flex items-center gap-1 text-xs text-slate-300 hover:text-white transition-colors"
                            >
                              {configCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                              {configCopied ? 'Copied!' : 'Copy'}
                            </button>
                            <button
                              onClick={() => {
                                const blob = new Blob([configJson], { type: 'application/json' });
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a'); a.href = url; a.download = 'mcp_config.json'; a.click();
                              }}
                              className="flex items-center gap-1 text-xs text-slate-300 hover:text-white transition-colors"
                            >
                              <Download className="w-3.5 h-3.5" /> Download
                            </button>
                          </div>
                        </div>
                        <div className="bg-slate-950 p-4 overflow-x-auto">
                          <pre className="text-xs text-emerald-400 font-mono whitespace-pre">{configJson}</pre>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-5 border-t border-slate-100 bg-slate-50/50 flex justify-between items-center gap-3">
              <div className="text-xs font-semibold text-slate-500">
                {selectedTool.discoveredTools?.length > 0 && `${selectedFunctions.length} operation(s) selected`}
              </div>
              <div className="flex gap-2.5">
                <Button onClick={() => setSelectedTool(null)} variant="ghost" className="text-xs">Close</Button>
                {isProvisioned(selectedTool) ? (
                  <Button
                    onClick={handleModalAction}
                    className="!bg-emerald-600 hover:!bg-emerald-700 !text-white text-xs font-bold rounded-xl"
                    disabled={selectedTool.discoveredTools?.length > 0 && selectedFunctions.length === 0}
                  >
                    Update Operations / Access
                  </Button>
                ) : !isRequested(selectedTool) && !isInCart(selectedTool.id) ? (
                  <Button
                    onClick={handleModalAction}
                    className="!bg-indigo-600 hover:!bg-indigo-700 !text-white text-xs font-bold rounded-xl"
                    disabled={selectedTool.discoveredTools?.length > 0 && selectedFunctions.length === 0}
                  >
                    Add to Request Cart
                  </Button>
                ) : isRequested(selectedTool) ? (
                  <Button variant="secondary" disabled className="text-xs">Pending Approval</Button>
                ) : (
                  <Button variant="secondary" disabled className="text-xs">In Request Cart</Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
