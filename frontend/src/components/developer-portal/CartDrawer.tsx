"use client";

import React, { useState, useEffect } from 'react';
import { ShoppingCart, X, Trash2, CheckCircle, Clock } from 'lucide-react';
import { Button } from './Button';
import { Badge } from './Badge';
import { usePortalContext } from '@/app/developer-portal/context';
import { useAuthStore } from '@/stores/auth-store';

export const CartDrawer = () => {
  const {
    isCartOpen, setIsCartOpen,
    cart, setCart,
    refreshData,
  } = usePortalContext();
  const { user, token } = useAuthStore();
  
  const [email, setEmail] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ provisioned: number; requested: number } | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (user?.email) {
      setEmail(user.email);
    }
  }, [user]);

  if (!isCartOpen) return null;

  const handleRemove = (id: string) => {
    setCart((prev: any[]) => prev.filter(item => item.id !== id));
  };

  const handleSubmit = async () => {
    setErrorMsg("");
    if (!email) { setErrorMsg("Please enter your email address."); return; }
    if (reason.length < 10) { setErrorMsg("Please enter a business justification (min 10 chars)."); return; }

    setSubmitting(true);

    const toProvision: any[] = [];
    const toRequest: any[] = [];
    cart.forEach((item: any) => {
      if (item.requiresApproval === false) {
        toProvision.push(item);
      } else {
        toRequest.push(item);
      }
    });

    try {
      if (toRequest.length > 0) {
        const tools = toRequest.filter((i: any) => !i.isBundle);
        const bundles = toRequest.filter((i: any) => i.isBundle);

        const payload: any = {
          requester_email: email,
          reason: reason,
          requested_mcp_tools: tools.map((t: any) => t.id || t.name),
          requested_mcp_tool: tools[0]?.name || bundles[0]?.name || 'MCP Tool',
          action: 'mcp_access_request',
        };
        if (bundles.length > 0) payload.requested_bundle_id = bundles[0].id;

        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/v1/approvals/mcp-access-request", {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          setErrorMsg(err.detail || "Failed to submit request. Please try again.");
          setSubmitting(false);
          return;
        }
      }

      setResult({ provisioned: toProvision.length, requested: toRequest.length });
      setCart([]);
      await refreshData();

    } catch (error) {
      setErrorMsg("An unexpected error occurred.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div
        className="absolute inset-0 bg-gray-900/40 backdrop-blur-sm transition-opacity"
        onClick={() => { setIsCartOpen(false); setResult(null); }}
      />
      <div className="fixed inset-y-0 right-0 max-w-md w-full flex">
        <div className="w-full h-full bg-white shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-gray-200 bg-gray-50/50">
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <ShoppingCart className="w-5 h-5 text-indigo-600" />
              Access Request Cart
              {cart.length > 0 && (
                <span className="ml-1 bg-indigo-600 text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">
                  {cart.length}
                </span>
              )}
            </h2>
            <button
              onClick={() => { setIsCartOpen(false); setResult(null); }}
              className="p-2 text-gray-400 hover:text-gray-900 rounded-full hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-5">
            {result ? (
              <div className="h-full flex flex-col items-center justify-center text-center space-y-4 px-4">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center ring-4 ring-green-50">
                  <CheckCircle className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="text-lg font-bold text-gray-900">Request Processed!</h3>
                <div className="space-y-2 w-full">
                  {result.provisioned > 0 && (
                    <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
                      <CheckCircle className="w-4 h-4 text-green-600 shrink-0" />
                      <span><strong>{result.provisioned}</strong> tool(s) active and ready for your agents.</span>
                    </div>
                  )}
                  {result.requested > 0 && (
                    <div className="flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
                      <Clock className="w-4 h-4 text-amber-600 shrink-0" />
                      <span><strong>{result.requested}</strong> tool(s) queued for Security Admin approval.</span>
                    </div>
                  )}
                </div>
                <Button variant="primary" className="mt-4 w-full !bg-indigo-600" onClick={() => { setIsCartOpen(false); setResult(null); }}>
                  Done
                </Button>
              </div>
            ) : cart.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center space-y-3">
                <ShoppingCart className="w-12 h-12 text-gray-300" />
                <p className="text-gray-500 font-medium">Your request cart is empty.</p>
                <Button variant="ghost" onClick={() => setIsCartOpen(false)}>Browse Catalogue</Button>
              </div>
            ) : (
              <div className="space-y-4">
                {cart.map((item: any) => (
                  <div key={item.id} className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm relative">
                    <button
                      onClick={() => handleRemove(item.id)}
                      className="absolute top-3 right-3 text-gray-300 hover:text-red-500 transition-colors"
                      title="Remove"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <div className="flex items-start gap-3 pr-6">
                      <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600 shrink-0">
                        <ShoppingCart className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-gray-900 text-sm truncate">{item.name}</h4>
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{item.description}</p>
                        {item.selectedFunctions?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {item.selectedFunctions.slice(0, 3).map((fn: string) => (
                              <span key={fn} className="text-xs bg-indigo-50 text-indigo-700 border border-indigo-100 px-1.5 py-0.5 rounded font-mono">
                                {fn.split('-').slice(1).join('_') || fn}
                              </span>
                            ))}
                            {item.selectedFunctions.length > 3 && (
                              <span className="text-xs text-gray-400">+{item.selectedFunctions.length - 3} more</span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-gray-100 flex justify-between items-center">
                      <span className="text-xs text-gray-400">{item.isBundle ? 'Bundle' : 'Tool'}</span>
                      <Badge variant={item.requiresApproval === false ? 'success' : 'warning'}>
                        {item.requiresApproval === false ? '⚡ Instant' : '🔒 Needs Approval'}
                      </Badge>
                    </div>
                  </div>
                ))}

                {/* Request Form */}
                <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
                  <h3 className="text-sm font-semibold text-gray-900">Request Justification</h3>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Email Address *</label>
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      className="w-full rounded-lg border border-gray-300 p-2.5 text-sm focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="developer@example.com"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Business Justification *</label>
                    <textarea
                      value={reason}
                      onChange={e => setReason(e.target.value)}
                      rows={3}
                      className="w-full rounded-lg border border-gray-300 p-2.5 text-sm focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="Explain the agent use case and why access to these tools is required..."
                    />
                  </div>
                  {errorMsg && <p className="text-red-600 text-xs bg-red-50 border border-red-200 rounded-lg p-2.5">{errorMsg}</p>}
                </div>
              </div>
            )}
          </div>

          {/* Footer with submit */}
          {cart.length > 0 && !result && (
            <div className="p-5 border-t border-gray-200 bg-gray-50">
              <div className="flex flex-col gap-1.5 mb-3.5 text-xs text-gray-500">
                {cart.filter((i: any) => i.requiresApproval === false).length > 0 && (
                  <div className="flex items-center gap-2 text-emerald-700 font-medium">
                    <CheckCircle className="w-3.5 h-3.5" />
                    {cart.filter((i: any) => i.requiresApproval === false).length} tool(s) will be provisioned instantly
                  </div>
                )}
                {cart.filter((i: any) => i.requiresApproval !== false).length > 0 && (
                  <div className="flex items-center gap-2 text-amber-700 font-medium">
                    <Clock className="w-3.5 h-3.5" />
                    {cart.filter((i: any) => i.requiresApproval !== false).length} tool(s) require Security Admin review
                  </div>
                )}
              </div>
              <Button className="w-full !bg-indigo-600 hover:!bg-indigo-700" onClick={handleSubmit} disabled={submitting}>
                {submitting ? "Submitting..." : `Submit Access Request (${cart.length} item${cart.length > 1 ? 's' : ''})`}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
