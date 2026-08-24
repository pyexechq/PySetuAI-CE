"use client";

import { useState } from 'react';
import { ShieldOff, CheckCircle, AlertTriangle, Clock, FileText, ArrowRight } from 'lucide-react';
import { Button } from '@/components/developer-portal/Button';
import { Badge } from '@/components/developer-portal/Badge';
import { useAuthStore } from '@/stores/auth-store';
import { usePortalContext } from '../context';

const DLP_POLICIES = [
  { id: 'dlp-pii-01', name: 'PII Data Exfiltration Block', category: 'Data Privacy', risk: 'High', description: 'Blocks transmission of personally identifiable information (SSN, credit card, DOB) through AI prompts.' },
  { id: 'dlp-code-02', name: 'Source Code Exfiltration Block', category: 'IP Protection', risk: 'High', description: 'Prevents proprietary source code and internal architecture details from being sent to external LLM providers.' },
  { id: 'dlp-fin-03', name: 'Financial Data Restriction', category: 'Compliance', risk: 'Medium', description: 'Restricts transmission of financial records, account numbers, and unreleased earnings data.' },
  { id: 'dlp-health-04', name: 'Healthcare PHI Block', category: 'HIPAA', risk: 'High', description: 'Prevents Protected Health Information (PHI) from being included in AI agent prompts.' },
  { id: 'dlp-secret-05', name: 'Secret & Credential Leak Prevention', category: 'Security', risk: 'Critical', description: 'Detects and blocks API keys, secrets, passwords, and tokens from being exposed via AI prompts.' },
  { id: 'dlp-internal-06', name: 'Internal Document Classification', category: 'Data Governance', risk: 'Low', description: 'Warns when documents marked "Internal" or "Confidential" are referenced in agent inputs.' },
];

const DURATIONS = [
  { value: '1', label: '1 Day', description: 'Emergency short-term exemption' },
  { value: '7', label: '7 Days', description: 'Standard exception window' },
  { value: '30', label: '30 Days', description: 'Extended project exception' },
  { value: 'custom', label: 'Custom', description: 'Specify exact dates' },
];

const RISK_COLORS: Record<string, string> = {
  Low: 'bg-green-50 text-green-700 border-green-200',
  Medium: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  High: 'bg-orange-50 text-orange-700 border-orange-200',
  Critical: 'bg-red-50 text-red-700 border-red-200',
};

export default function DlpExceptionPage() {
  const { user, token } = useAuthStore();
  const { refreshData } = usePortalContext();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [selectedPolicy, setSelectedPolicy] = useState<any>(null);
  const [duration, setDuration] = useState('7');
  const [justification, setJustification] = useState('');
  const [useCase, setUseCase] = useState('');
  const [dataScope, setDataScope] = useState('');
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [requestId, setRequestId] = useState('');
  const [error, setError] = useState('');

  const canProceedStep1 = !!selectedPolicy;
  const canProceedStep2 = justification.length >= 20 && useCase.length > 0 && dataScope.length > 0;
  const canSubmit = acknowledged && !submitting;

  const handleSubmit = async () => {
    setError('');
    setSubmitting(true);
    try {
      const payload = {
        requester_email: user?.email || '',
        reason: `[DLP Exception Request]\nPolicy: ${selectedPolicy.name}\nUse Case: ${useCase}\nData Scope: ${dataScope}\nDuration: ${duration} day(s)\nJustification: ${justification}`,
        action: 'dlp_policy_exception',
        requested_mcp_tools: [],
        policy_id: selectedPolicy.id,
        policy_name: selectedPolicy.name,
        user_name: user?.name || user?.email || '',
      };

      const res = await fetch('/api/v1/approvals/mcp-access-request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        setRequestId(data.id ? `REQ-${data.id.toString().substring(0, 8).toUpperCase()}` : `REQ-${Math.floor(1000 + Math.random() * 9000)}`);
        setSubmitted(true);
        await refreshData();
      } else {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || 'Submission failed. Please try again.');
      }
    } catch {
      setError('An unexpected error occurred.');
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="max-w-lg mx-auto text-center space-y-6 py-16 animate-in fade-in duration-500">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
          <CheckCircle className="w-8 h-8 text-green-600" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Exception Request Submitted</h2>
          <p className="text-gray-500 mt-2">Your request has been sent to the Security Admin team for review.</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-6 text-left space-y-3 shadow-sm">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Request ID</span>
            <span className="font-mono font-bold text-gray-900">{requestId}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Policy</span>
            <span className="font-medium text-gray-900">{selectedPolicy?.name}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Requested Duration</span>
            <span className="font-medium text-gray-900">{duration} days</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Status</span>
            <Badge variant="warning">Pending Review</Badge>
          </div>
        </div>
        <div className="flex gap-3 justify-center">
          <Button variant="secondary" onClick={() => window.location.reload()}>Submit Another</Button>
          <Button variant="primary" onClick={() => window.location.href = '/developer-portal/requests'}>View My Requests</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="p-3 bg-orange-50 rounded-xl border border-orange-100">
          <ShieldOff className="w-6 h-6 text-orange-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">DLP Policy Exception Request</h1>
          <p className="text-sm text-gray-500 mt-1">Request a temporary exception to a Data Loss Prevention rule for your use case. All exceptions require Security Admin approval and are fully audited.</p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-2">
        {[{ n: 1, label: 'Select Policy' }, { n: 2, label: 'Business Case' }, { n: 3, label: 'Review & Submit' }].map((s, i) => (
          <div key={s.n} className="flex items-center gap-2 flex-1">
            <div className={`flex items-center gap-2 ${step === s.n ? 'text-blue-600' : step > s.n ? 'text-green-600' : 'text-gray-400'}`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 ${step === s.n ? 'border-blue-600 bg-blue-50 text-blue-700' : step > s.n ? 'border-green-500 bg-green-50 text-green-700' : 'border-gray-300 bg-white text-gray-400'}`}>
                {step > s.n ? '✓' : s.n}
              </div>
              <span className="text-xs font-medium hidden sm:block">{s.label}</span>
            </div>
            {i < 2 && <div className={`flex-1 h-px ${step > s.n ? 'bg-green-300' : 'bg-gray-200'}`} />}
          </div>
        ))}
      </div>

      {/* Step 1: Select Policy */}
      {step === 1 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Select the DLP Policy to exempt</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {DLP_POLICIES.map(policy => (
              <label
                key={policy.id}
                className={`relative flex flex-col gap-3 p-4 rounded-xl border-2 cursor-pointer transition-all hover:shadow-sm ${selectedPolicy?.id === policy.id ? 'border-blue-500 bg-blue-50/30 ring-1 ring-blue-500' : 'border-gray-200 bg-white hover:border-blue-300'}`}
              >
                <input type="radio" className="sr-only" name="policy" value={policy.id} checked={selectedPolicy?.id === policy.id} onChange={() => setSelectedPolicy(policy)} />
                <div className="flex justify-between items-start">
                  <span className="font-semibold text-gray-900 text-sm pr-2">{policy.name}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border shrink-0 ${RISK_COLORS[policy.risk]}`}>{policy.risk}</span>
                </div>
                <p className="text-xs text-gray-500 leading-relaxed">{policy.description}</p>
                <Badge variant="default">{policy.category}</Badge>
              </label>
            ))}
          </div>
          <div className="flex justify-end pt-4">
            <Button onClick={() => setStep(2)} disabled={!canProceedStep1} className="gap-2">
              Next: Business Case <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Business Case */}
      {step === 2 && (
        <div className="space-y-6">
          <div className="flex items-center gap-3 p-4 bg-orange-50 border border-orange-200 rounded-lg text-sm text-orange-800">
            <AlertTriangle className="w-5 h-5 shrink-0 text-orange-500" />
            <span>You're requesting an exception to: <strong>{selectedPolicy?.name}</strong> (Risk: {selectedPolicy?.risk})</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1.5">Use Case / Project Name *</label>
              <input
                type="text"
                value={useCase}
                onChange={e => setUseCase(e.target.value)}
                className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., RAG pipeline for HR docs Q&A"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1.5">Data Scope *</label>
              <input
                type="text"
                value={dataScope}
                onChange={e => setDataScope(e.target.value)}
                className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., Employee onboarding documents (non-PII)"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 mb-1.5">Duration of Exception *</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {DURATIONS.map(d => (
                <label key={d.value} className={`flex flex-col p-3 rounded-lg border-2 cursor-pointer transition-all ${duration === d.value ? 'border-blue-500 bg-blue-50/30' : 'border-gray-200 bg-white hover:border-blue-300'}`}>
                  <input type="radio" className="sr-only" name="duration" value={d.value} checked={duration === d.value} onChange={() => setDuration(d.value)} />
                  <span className="font-bold text-sm text-gray-900">{d.label}</span>
                  <span className="text-[11px] text-gray-500 mt-0.5">{d.description}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 mb-1.5">
              Business Justification * <span className="font-normal text-gray-400">(min 20 chars)</span>
            </label>
            <textarea
              value={justification}
              onChange={e => setJustification(e.target.value)}
              rows={4}
              className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-blue-500 focus:border-blue-500"
              placeholder="Explain why this exception is necessary, what safeguards will be in place, and how data will be protected during the exception period..."
            />
            <p className="text-xs text-gray-400 mt-1 text-right">{justification.length} chars {justification.length < 20 && `(${20 - justification.length} more needed)`}</p>
          </div>

          <div className="flex justify-between pt-2">
            <Button variant="ghost" onClick={() => setStep(1)}>← Back</Button>
            <Button onClick={() => setStep(3)} disabled={!canProceedStep2} className="gap-2">
              Next: Review <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Review & Submit */}
      {step === 3 && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold">Review Your Request</h2>

          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <div className="px-5 py-4 bg-gray-50 border-b border-gray-200">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-gray-500" /> Request Summary
              </h3>
            </div>
            <div className="divide-y divide-gray-100">
              {[
                { label: 'Requester', value: `${user?.name} (${user?.email})` },
                { label: 'Policy', value: selectedPolicy?.name },
                { label: 'Risk Level', value: selectedPolicy?.risk },
                { label: 'Use Case', value: useCase },
                { label: 'Data Scope', value: dataScope },
                { label: 'Duration', value: `${duration} day(s)` },
                { label: 'Role', value: user?.role?.replace('_', ' ') },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-start px-5 py-3 text-sm gap-4">
                  <span className="text-gray-500 w-32 shrink-0">{label}</span>
                  <span className="font-medium text-gray-900 capitalize">{value}</span>
                </div>
              ))}
              <div className="px-5 py-3 text-sm">
                <span className="text-gray-500 block mb-1">Justification</span>
                <p className="text-gray-800 leading-relaxed">{justification}</p>
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <Clock className="w-5 h-5 text-yellow-600 shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-800">
              <strong className="block">Expected review time: 24–48 hours</strong>
              The Security Admin team will review your request and may reach out for clarification before approval.
            </div>
          </div>

          <label className="flex items-start gap-3 p-4 bg-white border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
            <input
              type="checkbox"
              className="mt-0.5 w-4 h-4 text-blue-600 rounded"
              checked={acknowledged}
              onChange={e => setAcknowledged(e.target.checked)}
            />
            <span className="text-sm text-gray-700 leading-relaxed">
              I acknowledge that this exception will be logged in the compliance audit trail, that I am responsible for ensuring data is handled securely during the exception period, and that misuse may result in revocation and disciplinary action.
            </span>
          </label>

          {error && <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>}

          <div className="flex justify-between pt-2">
            <Button variant="ghost" onClick={() => setStep(2)}>← Back</Button>
            <Button onClick={handleSubmit} disabled={!canSubmit} className="gap-2">
              {submitting ? 'Submitting...' : 'Submit Exception Request'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
