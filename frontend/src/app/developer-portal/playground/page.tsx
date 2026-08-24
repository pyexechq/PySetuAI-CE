"use client";

import { useState, useRef, useEffect, Suspense } from 'react';
import { Key, Terminal, Send, Activity, Copy, Check, ChevronDown, ChevronRight, Braces } from 'lucide-react';
import { Badge } from '@/components/developer-portal/Badge';
import { Button } from '@/components/developer-portal/Button';
import { usePortalContext } from '../context';
import { useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';

function PlaygroundContent() {
  const { apiKeys } = usePortalContext();
  const { token } = useAuthStore();
  const searchParams = useSearchParams();
  const initialKey = searchParams?.get('keyId') || '';

  const [activeKeyId, setActiveKeyId] = useState<string>(initialKey);
  const [messages, setMessages] = useState<any[]>([
    { role: 'assistant', content: 'Select an API key above to initialize your agent and begin testing.' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);
  const [configCopied, setConfigCopied] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeKey = apiKeys.find((k: any) => k.id === activeKeyId);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  useEffect(() => {
    if (initialKey && apiKeys.some((k: any) => k.id === initialKey)) {
      setActiveKeyId(initialKey);
    } else if (!activeKeyId && apiKeys.length > 0) {
      setActiveKeyId(apiKeys[0].id);
    }
  }, [apiKeys, initialKey]);

  useEffect(() => {
    if (activeKey) {
      setMessages([{
        role: 'assistant',
        content: `Agent initialized with **${activeKey.name}** (${activeKey.bundleName || 'Default Governance'}). ${activeKey.attachedTools?.length > 0 ? `${activeKey.attachedTools.length} MCP tool(s) attached. Ready for prompts.` : 'Standard guardrails enabled.'}`
      }]);
    } else if (apiKeys.length === 0) {
      setMessages([{ role: 'assistant', content: 'No API keys found. Please generate a Client API Key on the API Keys page to begin testing.' }]);
    }
  }, [activeKeyId, activeKey, apiKeys.length]);

  const handleSend = async () => {
    if (!input.trim() || !activeKey) return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setIsTyping(true);

    try {
      const messagesPayload = [
        ...messages.filter(m => m.role === 'user' || m.role === 'assistant').map(m => ({ role: m.role, content: m.content })),
        { role: 'user', content: userMsg }
      ];

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      } else if (activeKey.value && !activeKey.value.includes('•')) {
        headers["Authorization"] = `Bearer ${activeKey.value}`;
      }

      const res = await fetch("/api/v1/chat/completions", {
        method: "POST",
        headers,
        body: JSON.stringify({
          model: "gpt-4o-mini",
          messages: messagesPayload,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const choice = data.choices?.[0];
        if (choice?.message?.tool_calls?.length > 0) {
          const tc = choice.message.tool_calls[0];
          setMessages(prev => [
            ...prev,
            {
              role: 'tool_call',
              toolName: tc.function?.name || 'mcp_tool',
              payload: tc.function?.arguments || '{}',
            },
            {
              role: 'assistant',
              content: choice.message.content || `Executed tool \`${tc.function?.name}\` via PySetu AI Gateway.`,
            }
          ]);
        } else if (choice?.message?.content) {
          setMessages(prev => [
            ...prev,
            { role: 'assistant', content: choice.message.content }
          ]);
        } else {
          setMessages(prev => [
            ...prev,
            { role: 'assistant', content: "Prompt evaluated through PySetu AI Gateway successfully." }
          ]);
        }
      } else {
        const errData = await res.json().catch(() => ({}));
        if (res.status === 403 || res.status === 400 || res.status === 429) {
          setMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `🛡️ **PySetu Guardrail Triggered** (${res.status}):\n${errData.detail || 'Request intercepted by policy rule.'}`
            }
          ]);
        } else {
          setMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `PySetu AI Gateway evaluated prompt: **"${userMsg}"**.\n\n• Key: \`${activeKey.name}\`\n• Bundle: \`${activeKey.bundleName || 'Default'}\`\n• Gateway Status: ${res.status}`
            }
          ]);
        }
      }
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Evaluated via PySetu Gateway for key **${activeKey.name}**.` }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  // Build the MCP config JSON from the active key's attached tools
  const buildMCPConfig = () => {
    if (!activeKey?.attachedTools?.length) return null;
    const mcpServers: Record<string, any> = {};
    activeKey.attachedTools.forEach((t: any) => {
      if (t.serverConfig) {
        const key = t.name.replace(/\s+/g, '-').toLowerCase();
        mcpServers[key] = t.serverConfig;
      }
    });
    if (Object.keys(mcpServers).length === 0) return null;
    return JSON.stringify({ mcpServers }, null, 2);
  };

  const mcpConfigJson = buildMCPConfig();

  const handleCopyConfig = () => {
    if (mcpConfigJson) {
      navigator.clipboard.writeText(mcpConfigJson);
      setConfigCopied(true);
      setTimeout(() => setConfigCopied(false), 2000);
    }
  };

  return (
    <div className="flex h-[calc(100vh-140px)] gap-6 animate-in fade-in duration-500">
      {/* Sidebar */}
      <div className="w-80 flex flex-col gap-4 overflow-y-auto">
        {/* Key Selector */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Key className="w-4 h-4 text-blue-600" /> Active API Key
          </h3>
          <select
            value={activeKeyId}
            onChange={(e) => setActiveKeyId(e.target.value)}
            className="w-full text-sm border-gray-300 border rounded-md focus:ring-blue-500 focus:border-blue-500 bg-gray-50 p-2"
          >
            <option value="" disabled>Select a key to test...</option>
            {apiKeys.map((k: any) => (
              <option key={k.id} value={k.id}>{k.name} ({k.environment})</option>
            ))}
          </select>

          {activeKey && (
            <div className="mt-4 pt-4 border-t border-gray-100 space-y-2">
              <div className="flex justify-between text-xs text-gray-500">
                <span>Model:</span>
                <span className="font-medium text-gray-900">{activeKey.model.name}</span>
              </div>
              <div className="flex justify-between text-xs text-gray-500">
                <span>Environment:</span>
                <Badge variant={activeKey.environment === 'Production' ? 'danger' : 'primary'}>{activeKey.environment}</Badge>
              </div>

              {/* Attached Tools */}
              <div className="pt-2 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-900 mb-2">Attached MCP Tools ({activeKey.attachedTools.length})</p>
                {activeKey.attachedTools.length > 0 ? (
                  <div className="space-y-1.5">
                    {activeKey.attachedTools.map((t: any) => (
                      <div key={t.id} className="flex items-center gap-2 text-xs bg-gray-50 p-2 rounded border border-gray-100">
                        <Braces className="w-3.5 h-3.5 text-purple-500 shrink-0" />
                        <span className="truncate flex-1 font-medium">{t.name}</span>
                        {t.selectedFunctions?.length > 0 && (
                          <span className="text-gray-400 shrink-0">{t.selectedFunctions.length} fn</span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 italic">No tools attached.</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* GAP 6 — MCP Config Snippet */}
        {activeKey && mcpConfigJson && (
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
            <button
              onClick={() => setConfigOpen(!configOpen)}
              className="w-full flex items-center justify-between p-4 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <span className="flex items-center gap-2">
                <Braces className="w-4 h-4 text-gray-400" />
                MCP Config
              </span>
              {configOpen ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
            </button>
            {configOpen && (
              <div>
                <div className="flex items-center justify-between bg-gray-800 px-3 py-1.5">
                  <span className="text-[10px] text-gray-400 font-mono">claude_desktop_config.json</span>
                  <button
                    onClick={handleCopyConfig}
                    className="flex items-center gap-1 text-[10px] text-gray-400 hover:text-white transition-colors"
                  >
                    {configCopied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
                    {configCopied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <div className="bg-gray-900 p-3 overflow-x-auto max-h-48">
                  <pre className="text-[10px] text-green-400 font-mono whitespace-pre">{mcpConfigJson}</pre>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tip */}
        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 text-xs text-blue-800 leading-relaxed">
          <strong className="block mb-1">💡 Tip</strong>
          The MCP Config above can be pasted directly into your Claude Desktop or agent configuration file to enable the attached tools locally.
        </div>
      </div>

      {/* Chat Console */}
      <div className="flex-1 bg-white border border-gray-200 rounded-lg shadow-sm flex flex-col overflow-hidden">
        <div className="p-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <Terminal className="w-5 h-5 text-gray-600" /> Interactive Test Console
          </h3>
          {activeKey && <Badge variant="success">Agent Ready</Badge>}
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/30">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-lg p-4 ${
                msg.role === 'user' ? 'bg-blue-600 text-white' :
                msg.role === 'tool_call' ? 'bg-gray-900 text-gray-100 font-mono text-sm w-full shadow-inner' :
                'bg-white border border-gray-200 text-gray-800 shadow-sm'
              }`}>
                {msg.role === 'tool_call' ? (
                  <div>
                    <div className="flex items-center gap-2 mb-2 text-gray-400 border-b border-gray-700 pb-2">
                      <Activity className="w-4 h-4 text-yellow-400" />
                      <span className="font-bold text-yellow-300">Tool Invocation:</span>
                      <span className="text-green-400">{msg.toolName}</span>
                    </div>
                    <pre className="overflow-x-auto text-xs text-green-400"><code>{msg.payload}</code></pre>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                )}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm flex items-center gap-2 text-sm text-gray-500">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
                <span className="ml-1">Agent is processing...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 bg-white border-t border-gray-200">
          <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={!activeKey || isTyping}
              placeholder={activeKey ? "Send a prompt to test your agent..." : "Select an API key first"}
              className="flex-1 bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 p-3"
            />
            <Button type="submit" variant="primary" disabled={!activeKey || isTyping || !input.trim()} className="!px-6">
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function PlaygroundPage() {
  return (
    <Suspense fallback={<div className="p-8 text-gray-500">Loading playground...</div>}>
      <PlaygroundContent />
    </Suspense>
  );
}
