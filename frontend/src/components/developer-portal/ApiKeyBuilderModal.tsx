"use client";

import React, { useState, useEffect } from 'react';
import { Key, X, Check, Copy, Download, CheckCircle, ShieldCheck, Cpu } from 'lucide-react';
import { Button } from './Button';
import { useAuthStore } from '@/stores/auth-store';

export const ApiKeyBuilderModal = ({ isOpen, onClose, onSubmit, provisionedTools, environment }: any) => {
  const { token } = useAuthStore();
  const [step, setStep] = useState(1);
  const [keyName, setKeyName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedBundleId, setSelectedBundleId] = useState<string>('');
  const [availableBundles, setAvailableBundles] = useState<any[]>([]);
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedKeyData, setGeneratedKeyData] = useState<any>(null);
  const [activeLangTab, setActiveLangTab] = useState('python');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setKeyName('');
      setDescription('');
      setSelectedTools([]);
      setGeneratedKeyData(null);
      setCopied(false);
      setError('');

      // Fetch policy bundles
      if (token) {
        fetch('/api/v1/access/policy-bundles', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
          .then(res => res.ok ? res.json() : [])
          .then(data => {
            setAvailableBundles(data || []);
            if (data?.length > 0) {
              const defaultBundle = data.find((b: any) => b.is_default) || data[0];
              setSelectedBundleId(defaultBundle.id);
            }
          })
          .catch(() => setAvailableBundles([]));
      }
    }
  }, [isOpen, token]);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    if (!keyName.trim()) {
      setError('Key name is required');
      return;
    }
    setError('');
    setIsGenerating(true);

    try {
      const res = await fetch('/api/v1/client-api-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: keyName.trim(),
          description: description.trim() || `Generated via Developer Portal (${environment})`,
          bundle_id: selectedBundleId || undefined,
          client_response_protocol: 'openai',
          token_saving_enabled: true,
          token_saving_mode: 'balanced',
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to create API key (${res.status})`);
      }

      const createdKey = await res.json();
      const selectedBundle = availableBundles.find(b => b.id === selectedBundleId);

      const formattedKey = {
        id: createdKey.id,
        name: createdKey.name,
        value: createdKey.api_key,
        createdAt: new Date().toLocaleDateString(),
        environment: environment,
        bundleName: createdKey.bundle_name || selectedBundle?.name || 'Default Policy Bundle',
        model: { name: createdKey.bundle_name || selectedBundle?.name || 'PySetu Default Bundle', provider: 'PySetu AI Gateway' },
        attachedTools: provisionedTools.filter((t: any) => selectedTools.includes(t.id)),
      };

      setGeneratedKeyData(formattedKey);
      setStep(2);
      if (onSubmit) onSubmit(formattedKey);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred while generating key');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const apiEndpoint = typeof window !== 'undefined' ? `${window.location.origin}/api/v1/gateway` : 'https://api.pysetu.ai/api/v1/gateway';

  const snippets: any = generatedKeyData ? {
    python: `import os\nfrom openai import OpenAI\n\n# Initialize client pointing to PySetu AI Gateway\nclient = OpenAI(\n    base_url="${apiEndpoint}",\n    api_key="${generatedKeyData.value}"\n)\n\nresponse = client.chat.completions.create(\n    model="gpt-4o",\n    messages=[{"role": "user", "content": "Analyze my recent database logs"}]\n)\nprint(response.choices[0].message.content)`,
    node: `import OpenAI from 'openai';\n\nconst client = new OpenAI({\n  baseURL: '${apiEndpoint}',\n  apiKey: '${generatedKeyData.value}'\n});\n\nasync function main() {\n  const res = await client.chat.completions.create({\n    model: 'gpt-4o',\n    messages: [{ role: 'user', content: 'Analyze my recent database logs' }]\n  });\n  console.log(res.choices[0].message.content);\n}\nmain();`,
    curl: `curl -X POST ${apiEndpoint}/chat/completions \\\n  -H "Authorization: Bearer ${generatedKeyData.value}" \\\n  -H "Content-Type: application/json" \\\n  -d '{\n    "model": "gpt-4o",\n    "messages": [{"role": "user", "content": "Analyze my recent database logs"}]\n  }'`
  } : {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 p-4 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl bg-white rounded-xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden transition-all">
        {step === 1 ? (
          <>
            <div className="flex items-center justify-between p-5 border-b bg-gray-50/50">
              <div>
                <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                  <Key className="w-5 h-5 text-indigo-600" /> Create Client API Key
                </h3>
                <p className="text-sm text-gray-500 mt-1">Configure your agent's governance bundle and access scope.</p>
              </div>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-900 p-1"><X className="w-5 h-5" /></button>
            </div>

            <div className="p-6 space-y-5 overflow-y-auto flex-1">
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {error}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block mb-1.5 text-sm font-medium text-gray-900">Key Name *</label>
                  <input
                    type="text"
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    placeholder="e.g., CI/CD Deployment Agent" 
                    className="bg-white border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-full p-2.5"
                  />
                </div>
                <div>
                  <label className="block mb-1.5 text-sm font-medium text-gray-900 flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-green-600" /> Governance Policy Bundle
                  </label>
                  <select
                    value={selectedBundleId}
                    onChange={(e) => setSelectedBundleId(e.target.value)}
                    className="bg-white border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-full p-2.5"
                  >
                    {availableBundles.length === 0 ? (
                      <option value="">Default Tenant Policy Bundle</option>
                    ) : (
                      availableBundles.map(b => (
                        <option key={b.id} value={b.id}>
                          {b.name} {b.is_default ? '(Default)' : ''}
                        </option>
                      ))
                    )}
                  </select>
                </div>
              </div>

              <div>
                <label className="block mb-1.5 text-sm font-medium text-gray-900">Description (Optional)</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g., Agent service key for automated customer onboarding" 
                  className="bg-white border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-full p-2.5"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">Attach Provisioned Tools ({provisionedTools.length} Available)</label>
                <div className="space-y-2 max-h-52 overflow-y-auto p-1">
                  {provisionedTools.map((tool: any) => (
                    <label key={tool.id} className={`flex items-start p-3 cursor-pointer rounded-lg border transition-all ${selectedTools.includes(tool.id) ? 'border-indigo-500 bg-indigo-50/30 ring-1 ring-indigo-500' : 'border-gray-200 bg-white hover:border-indigo-300'}`}>
                      <input
                        type="checkbox"
                        className="mt-1 w-4 h-4 text-indigo-600 rounded" 
                        checked={selectedTools.includes(tool.id)}
                        onChange={() => setSelectedTools(prev => prev.includes(tool.id) ? prev.filter(id => id !== tool.id) : [...prev, tool.id])}
                      />
                      <div className="ml-3">
                        <span className="font-medium text-gray-900 text-sm">{tool.name}</span>
                        <p className="text-gray-500 text-xs mt-0.5">{tool.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex justify-end p-5 border-t bg-gray-50 gap-3">
              <Button variant="ghost" onClick={onClose}>Cancel</Button>
              <Button variant="primary" onClick={handleGenerate} disabled={isGenerating || !keyName.trim()}>
                {isGenerating ? 'Generating...' : 'Generate Key'}
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="p-6 text-center border-b bg-green-50/50">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                <Check className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900">API Key Created & Stored</h3>
              <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
                Please copy this secret key now. For security reasons, the unmasked plaintext <strong className="text-gray-700">will not be displayed again</strong>.
              </p>
            </div>

            <div className="p-6 space-y-6 overflow-y-auto flex-1 bg-white">
              <div className="relative group">
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Secret Key</label>
                <div className="flex items-center gap-2">
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 font-mono text-sm text-gray-800 flex-1 break-all select-all">
                    {generatedKeyData?.value}
                  </div>
                  <Button variant="secondary" onClick={() => handleCopy(generatedKeyData?.value)} className="shrink-0">
                    {copied ? <CheckCircle className="w-4 h-4 text-green-600 mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
                    {copied ? 'Copied' : 'Copy'}
                  </Button>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Gateway Quickstart</label>
                  <Button
                    variant="ghost"
                    className="!text-xs !py-1 !px-2 text-indigo-600 hover:text-indigo-700 h-auto"
                    onClick={() => handleCopy(`PYSETU_API_KEY=${generatedKeyData?.value}\nPYSETU_GATEWAY_URL=${apiEndpoint}`)}
                  >
                    <Download className="w-3 h-3 mr-1" /> Copy .env
                  </Button>
                </div>
                
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="flex bg-gray-50 border-b border-gray-200">
                    {['python', 'node', 'curl'].map(lang => (
                      <button
                        key={lang}
                        onClick={() => setActiveLangTab(lang)}
                        className={`px-4 py-2 text-xs font-medium capitalize ${activeLangTab === lang ? 'bg-white border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
                      >
                        {lang === 'node' ? 'Node.js' : lang}
                      </button>
                    ))}
                  </div>
                  <div className="bg-gray-900 p-4 relative group">
                    <button
                      onClick={() => handleCopy(snippets[activeLangTab])}
                      className="absolute top-2 right-2 p-1.5 bg-gray-800 text-gray-400 hover:text-white rounded opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                    <pre className="text-gray-300 font-mono text-xs overflow-x-auto whitespace-pre">
                      <code>{snippets[activeLangTab]}</code>
                    </pre>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end p-5 border-t bg-gray-50">
              <Button variant="primary" onClick={onClose}>I have saved my key</Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
