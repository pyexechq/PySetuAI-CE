"use client";

import { useState } from 'react';
import { ClipboardList, Clock, CheckCircle2, XCircle, ShieldAlert, Flame, Package, Filter, RotateCw } from 'lucide-react';
import { Badge } from '@/components/developer-portal/Badge';
import { usePortalContext } from '../context';

export default function RequestsPage() {
  const { requestedTools, refreshData, loading } = usePortalContext();
  const [filterType, setFilterType] = useState<'all' | 'mcp' | 'dlp' | 'break_glass'>('all');

  const filteredRequests = requestedTools.filter(req => {
    if (filterType === 'all') return true;
    if (filterType === 'mcp') return req.action === 'mcp_access_request';
    if (filterType === 'dlp') return req.action === 'dlp_policy_exception';
    if (filterType === 'break_glass') return req.action === 'break_glass_test';
    return true;
  });

  const getActionBadge = (action: string) => {
    if (action === 'dlp_policy_exception') {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] text-amber-700 bg-amber-50 border border-amber-200/80 px-2 py-0.5 rounded-full font-semibold">
          <ShieldAlert className="w-3 h-3" /> DLP Exception
        </span>
      );
    }
    if (action === 'break_glass_test') {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] text-rose-700 bg-rose-50 border border-rose-200/80 px-2 py-0.5 rounded-full font-semibold">
          <Flame className="w-3 h-3" /> Break Glass
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-[11px] text-indigo-700 bg-indigo-50 border border-indigo-200/80 px-2 py-0.5 rounded-full font-semibold">
        <Package className="w-3 h-3" /> MCP Tool Access
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    if (status === 'Approved') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200/80 px-2.5 py-1 rounded-full font-bold">
          <CheckCircle2 className="w-3.5 h-3.5" /> Approved
        </span>
      );
    }
    if (status === 'Rejected') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-rose-700 bg-rose-50 border border-rose-200/80 px-2.5 py-1 rounded-full font-bold">
          <XCircle className="w-3.5 h-3.5" /> Rejected
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-xs text-amber-700 bg-amber-50 border border-amber-200/80 px-2.5 py-1 rounded-full font-bold">
        <Clock className="w-3.5 h-3.5" /> Pending Review
      </span>
    );
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">Access &amp; Exception Requests</h1>
          <p className="text-sm font-medium text-slate-500 mt-1">
            Track approval status for requested MCP capabilities, DLP exemptions, and emergency test cases.
          </p>
        </div>
        <button
          onClick={() => refreshData()}
          className="inline-flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800 font-bold px-3 py-1.5 border border-indigo-200 rounded-xl bg-indigo-50/60 hover:bg-indigo-100 transition-colors shadow-xs"
        >
          <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh Status
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-slate-200/60 pb-3">
        {[
          { id: 'all', label: 'All Requests', count: requestedTools.length },
          { id: 'mcp', label: 'MCP Tools', count: requestedTools.filter(r => r.action === 'mcp_access_request').length },
          { id: 'dlp', label: 'DLP Exceptions', count: requestedTools.filter(r => r.action === 'dlp_policy_exception').length },
          { id: 'break_glass', label: 'Break Glass', count: requestedTools.filter(r => r.action === 'break_glass_test').length },
        ].map(tab => {
          const isActive = filterType === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setFilterType(tab.id as any)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-white border border-slate-200/80 text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <span>{tab.label}</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                isActive ? 'bg-indigo-700 text-white' : 'bg-slate-100 text-slate-500'
              }`}>
                {tab.count}
              </span>
            </button>
          );
        })}
      </div>

      <div className="bg-white border border-slate-200/80 rounded-2xl shadow-[0_4px_20px_-4px_rgba(0,0,0,0.03)] overflow-hidden">
        {filteredRequests.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <ClipboardList className="w-12 h-12 text-slate-300 mb-3" />
            <h3 className="text-base font-bold text-slate-900">No Requests in this View</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm">
              Submit a request from the Tool Catalogue, DLP Exception, or Break Glass pages to track it here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50/60">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Request ID</th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Type &amp; Target</th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Submitted</th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Review Decision</th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100 text-sm">
                {filteredRequests.map((req) => (
                  <tr key={req.requestId} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="font-mono text-xs font-bold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-lg border border-indigo-100">
                        {req.requestId}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 mb-1">
                        {getActionBadge(req.action)}
                      </div>
                      <div className="font-bold text-slate-900 text-sm">{req.toolName}</div>
                      {req.selectedFunctions?.length > 0 && req.action === 'mcp_access_request' && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {req.selectedFunctions.map((fn: string) => (
                            <span key={fn} className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">
                              {fn}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-500 font-medium">
                      {req.submittedAt}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500">
                      {req.decidedBy ? (
                        <div>
                          <span className="font-bold text-slate-800">{req.decidedBy}</span>
                          <span className="text-slate-400 block text-[11px] mt-0.5">{req.decidedAt}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">Pending Security Admin</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(req.status)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
