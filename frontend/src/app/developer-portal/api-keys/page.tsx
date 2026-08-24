"use client";

import { useState } from 'react';
import { KeyRound, Plus, Trash2, ShieldCheck, Play, Copy, CheckCircle, Eye, EyeOff, Search, RotateCw, Activity } from 'lucide-react';
import { Button } from '@/components/developer-portal/Button';
import { ApiKeyBuilderModal } from '@/components/developer-portal/ApiKeyBuilderModal';
import { usePortalContext } from '../context';
import { useAuthStore } from '@/stores/auth-store';
import { useRouter } from 'next/navigation';

export default function ApiKeysPage() {
  const { environment, apiKeys, refreshData, provisionedTools, loading } = usePortalContext();
  const { token } = useAuthStore();
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [revealedKeys, setRevealedKeys] = useState<Record<string, string>>({});
  const [revealingId, setRevealingId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const router = useRouter();

  const handleReveal = async (keyId: string) => {
    if (revealedKeys[keyId]) {
      // Toggle off
      setRevealedKeys(prev => {
        const next = { ...prev };
        delete next[keyId];
        return next;
      });
      return;
    }

    setRevealingId(keyId);
    try {
      const res = await fetch(`/api/v1/client-api-keys/${keyId}/reveal`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setRevealedKeys(prev => ({ ...prev, [keyId]: data.api_key }));
      } else {
        alert('This key was created before secret-reveal support or cannot be revealed.');
      }
    } catch {
      alert('Failed to reveal API key.');
    } finally {
      setRevealingId(null);
    }
  };

  const handleDelete = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key? This action is immediate and cannot be undone.')) {
      return;
    }
    setDeletingId(keyId);
    try {
      const res = await fetch(`/api/v1/client-api-keys/${keyId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok || res.status === 204) {
        await refreshData();
      } else {
        alert('Failed to delete key. Please try again.');
      }
    } catch {
      alert('An unexpected error occurred.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredKeys = apiKeys.filter(k => 
    k.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    k.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    k.bundleName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    k.keyPrefix?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold">Client API Keys</h1>
          <p className="text-sm text-gray-500 mt-1">
            Active credentials for your AI agents and applications ({apiKeys.length} total keys).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refreshData()}
            className="p-2 text-gray-500 hover:text-gray-900 border border-gray-200 rounded-lg bg-white hover:bg-gray-50 transition-colors"
            title="Refresh keys"
          >
            <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <Button onClick={() => setIsKeyModalOpen(true)} className="gap-2 !bg-indigo-600 hover:!bg-indigo-700">
            <Plus className="w-4 h-4"/> Create Client Key
          </Button>
        </div>
      </div>

      {/* Search Bar */}
      {apiKeys.length > 0 && (
        <div className="relative max-w-md">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search keys by name, description, or policy bundle..."
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      )}

      {/* Table / Empty State */}
      <div className="bg-white shadow-sm border border-gray-200 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            Loading API keys...
          </div>
        ) : filteredKeys.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <div className="h-12 w-12 rounded-full bg-indigo-50 flex items-center justify-center mb-3">
              <KeyRound className="w-6 h-6 text-indigo-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">
              {searchQuery ? 'No matching API keys found' : 'No API Keys Created Yet'}
            </h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm">
              {searchQuery ? 'Try clearing your search term.' : 'Generate a client key to authenticate your agent pipelines against the AI Gateway.'}
            </p>
            {!searchQuery && (
              <Button onClick={() => setIsKeyModalOpen(true)} className="mt-4 gap-2 !bg-indigo-600">
                <Plus className="w-4 h-4" /> Create API Key
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Name & Description</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Policy Bundle</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Secret Key</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Limits</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Created</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredKeys.map((key) => {
                  const isRevealed = Boolean(revealedKeys[key.id]);
                  const displayKey = isRevealed ? revealedKeys[key.id] : (key.maskedKey || key.value);

                  return (
                    <tr key={key.id} className="hover:bg-gray-50/80 transition-colors">
                      {/* Name & Desc */}
                      <td className="px-6 py-4">
                        <div className="font-semibold text-gray-900 text-sm flex items-center gap-2">
                          <KeyRound className="w-4 h-4 text-indigo-600 shrink-0" />
                          <span>{key.name}</span>
                          {key.isActive && (
                            <span className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.2 rounded-full font-medium">
                              Active
                            </span>
                          )}
                        </div>
                        {key.description && (
                          <p className="text-xs text-gray-500 mt-0.5 max-w-xs truncate">{key.description}</p>
                        )}
                      </td>

                      {/* Policy Bundle */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5 text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full w-fit">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                          <span>{key.bundleName || 'Default Governance'}</span>
                        </div>
                      </td>

                      {/* Key + Reveal + Copy */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className={`font-mono text-xs px-2.5 py-1 rounded border ${
                            isRevealed 
                              ? 'bg-amber-50 text-amber-900 border-amber-200 font-bold select-all'
                              : 'bg-gray-100 text-gray-700 border-gray-200'
                          }`}>
                            {displayKey}
                          </span>
                          
                          {/* Reveal Button */}
                          {key.revealable && (
                            <button
                              onClick={() => handleReveal(key.id)}
                              disabled={revealingId === key.id}
                              className="text-gray-400 hover:text-gray-700 p-1"
                              title={isRevealed ? "Hide Key" : "Reveal Plaintext Key"}
                            >
                              {isRevealed ? <EyeOff className="w-4 h-4 text-amber-600" /> : <Eye className="w-4 h-4" />}
                            </button>
                          )}

                          {/* Copy Button */}
                          <button
                            onClick={() => handleCopy(key.id, isRevealed ? revealedKeys[key.id] : displayKey)}
                            className="text-gray-400 hover:text-gray-700 p-1"
                            title="Copy Key"
                          >
                            {copiedId === key.id ? <CheckCircle className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                          </button>
                        </div>
                      </td>

                      {/* Rate / Token Limits */}
                      <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500">
                        {key.rateLimits?.rpm || key.rateLimits?.tpm ? (
                          <div className="space-y-0.5 text-[11px]">
                            {key.rateLimits?.rpm && <div>{key.rateLimits.rpm} req/min</div>}
                            {key.rateLimits?.tpm && <div>{(key.rateLimits.tpm / 1000)}k tok/min</div>}
                          </div>
                        ) : (
                          <span className="text-gray-400">Default Limits</span>
                        )}
                      </td>

                      {/* Created */}
                      <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500">
                        {key.createdAt}
                      </td>

                      {/* Actions */}
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => router.push(`/developer-portal/playground?keyId=${key.id}`)}
                          className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-900 mr-4 font-semibold"
                        >
                          <Play className="w-3.5 h-3.5" /> Test in Playground
                        </button>
                        <button
                          onClick={() => handleDelete(key.id)}
                          disabled={deletingId === key.id}
                          className="text-red-500 hover:text-red-700 disabled:opacity-50 p-1"
                          title="Revoke key"
                        >
                          <Trash2 className="w-4 h-4 inline" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ApiKeyBuilderModal
        isOpen={isKeyModalOpen}
        onClose={() => { setIsKeyModalOpen(false); refreshData(); }}
        onSubmit={() => { refreshData(); }}
        provisionedTools={provisionedTools}
        environment={environment}
      />
    </div>
  );
}
