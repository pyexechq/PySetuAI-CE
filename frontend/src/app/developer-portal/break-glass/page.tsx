"use client";

import { useState } from 'react';
import { Zap, AlertTriangle, CheckCircle, Shield, Clock, User, Server, GitBranch, FileText } from 'lucide-react';
import { Button } from '@/components/developer-portal/Button';
import { Badge } from '@/components/developer-portal/Badge';
import { useAuthStore } from '@/stores/auth-store';
import { usePortalContext } from '../context';

const SCENARIO_TYPES = [
  {
    id: 'policy-bypass-test',
    name: 'Policy Bypass Test',
    icon: Shield,
    iconColor: 'text-purple-600',
    iconBg: 'bg-purple-50',
    description: 'Validate that a security policy correctly blocks a specific type of prompt or data when executed via an agent.',
    examples: ['Test PII detection on structured data', 'Verify prompt injection guardrails', 'Test rate limit enforcement'],
  },
  {
    id: 'emergency-access',
    name: 'Emergency Access Override',
    icon: Zap,
    iconColor: 'text-yellow-600',
    iconBg: 'bg-yellow-50',
    description: 'Request temporary elevated access to a restricted tool or endpoint for an urgent incident response.',
    examples: ['Incident investigation access', 'Critical bug hotfix deployment', 'Emergency data retrieval'],
  },
  {
    id: 'red-team-simulation',
    name: 'Red Team Simulation',
    icon: AlertTriangle,
    iconColor: 'text-red-600',
    iconBg: 'bg-red-50',
    description: 'Submit a controlled adversarial test case to evaluate robustness of agent guardrails and DLP rules.',
    examples: ['Prompt injection attack simulation', 'Data exfiltration attempt test', 'Jailbreak resistance test'],
  },
  {
    id: 'compliance-test',
    name: 'Compliance Test Case',
    icon: FileText,
    iconColor: 'text-green-600',
    iconBg: 'bg-green-50',
    description: 'Run a controlled compliance test to validate regulatory controls are functioning as expected.',
    examples: ['GDPR data handling validation', 'HIPAA PHI protection test', 'SOC 2 access control check'],
  },
];

const SCOPES = [
  { id: 'scope-agent', label: 'Agent', icon: User, description: 'Scoped to a specific agent configuration' },
  { id: 'scope-endpoint', label: 'Endpoint', icon: Server, description: 'Scoped to a specific API endpoint' },
  { id: 'scope-policy', label: 'Policy Rule', icon: GitBranch, description: 'Targets a specific policy rule or bundle' },
];

const EXPIRY_OPTIONS = [
  { value: '2h', label: '2 Hours', description: 'Quick spot test' },
  { value: '8h', label: '8 Hours', description: 'Single work session' },
  { value: '24h', label: '24 Hours', description: 'Full test cycle' },
  { value: '72h', label: '72 Hours', description: 'Extended evaluation' },
];

export default function BreakGlassPage() {
  const { user, token } = useAuthStore();
  const { refreshData } = usePortalContext();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [selectedScenario, setSelectedScenario] = useState<any>(null);
  const [selectedScope, setSelectedScope] = useState<string>('');
  const [scopeTarget, setScopeTarget] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [expectedOutcome, setExpectedOutcome] = useState('');
  const [expiry, setExpiry] = useState('8h');
  const [acknowledged, setAcknowledged] = useState(false);
  const [complianceAck, setComplianceAck] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [requestId, setRequestId] = useState('');
  const [error, setError] = useState('');

  const canProceedStep1 = !!selectedScenario;
  const canProceedStep2 = title.length >= 5 && description.length >= 20 && selectedScope && scopeTarget.length > 0 && expectedOutcome.length > 0;
  const canSubmit = acknowledged && complianceAck && !submitting;

  const handleSubmit = async () => {
    setError('');
    setSubmitting(true);
    try {
      const payload = {
        requester_email: user?.email || '',
        reason: `[Break Glass Request]\nScenario: ${selectedScenario?.name}\nTitle: ${title}\nScope: ${selectedScope} — ${scopeTarget}\nExpiry: ${expiry}\nExpected Outcome: ${expectedOutcome}\nDescription: ${description}`,
        action: 'break_glass_test',
        requested_mcp_tools: [],
        user_name: user?.name || user?.email || '',
        policy_name: selectedScenario?.name || '',
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
        setRequestId(data.id ? `BG-${data.id.toString().substring(0, 8).toUpperCase()}` : `BG-${Math.floor(1000 + Math.random() * 9000)}`);
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
        <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto ring-4 ring-yellow-50">
          <Zap className="w-8 h-8 text-yellow-600" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Break Glass Request Submitted</h2>
          <p className="text-gray-500 mt-2">Your test case has been queued for Security Admin review. You'll be notified when approved.</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-6 text-left space-y-3 shadow-sm">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Request ID</span>
            <span className="font-mono font-bold text-gray-900">{requestId}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Scenario</span>
            <span className="font-medium text-gray-900">{selectedScenario?.name}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Expiry Window</span>
            <span className="font-medium text-gray-900">{expiry}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Status</span>
            <Badge variant="warning">Pending Approval</Badge>
          </div>
        </div>
        <div className="flex gap-3 justify-center">
          <Button variant="secondary" onClick={() => window.location.reload()}>New Request</Button>
          <Button variant="primary" onClick={() => window.location.href = '/developer-portal/requests'}>View My Requests</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="p-3 bg-yellow-50 rounded-xl border border-yellow-100">
          <Zap className="w-6 h-6 text-yellow-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Break Glass Request</h1>
          <p className="text-sm text-gray-500 mt-1">
            Submit a controlled break-glass test case or request emergency access override. All requests are time-limited, require approval, and are fully logged in the compliance audit trail.
          </p>
        </div>
      </div>

      <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
        <p className="text-sm text-red-800">
          <strong>Compliance Notice:</strong> Break glass requests trigger immediate notifications to the Security Admin, CISO, and compliance team. Misuse of this feature may result in disciplinary action. All activity during the exception window is recorded.
        </p>
      </div>

      {/* Progress */}
      <div className="flex items-center gap-2">
        {[{ n: 1, label: 'Scenario Type' }, { n: 2, label: 'Test Details' }, { n: 3, label: 'Review & Confirm' }].map((s, i) => (
          <div key={s.n} className="flex items-center gap-2 flex-1">
            <div className={`flex items-center gap-2 ${step === s.n ? 'text-yellow-600' : step > s.n ? 'text-green-600' : 'text-gray-400'}`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 ${step === s.n ? 'border-yellow-500 bg-yellow-50 text-yellow-700' : step > s.n ? 'border-green-500 bg-green-50 text-green-700' : 'border-gray-300 bg-white text-gray-400'}`}>
                {step > s.n ? '✓' : s.n}
              </div>
              <span className="text-xs font-medium hidden sm:block">{s.label}</span>
            </div>
            {i < 2 && <div className={`flex-1 h-px ${step > s.n ? 'bg-green-300' : 'bg-gray-200'}`} />}
          </div>
        ))}
      </div>

      {/* Step 1: Scenario Type */}
      {step === 1 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">What type of break-glass scenario is this?</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SCENARIO_TYPES.map(scenario => {
              const Icon = scenario.icon;
              return (
                <label
                  key={scenario.id}
                  className={`flex flex-col gap-3 p-5 rounded-xl border-2 cursor-pointer transition-all hover:shadow-sm ${selectedScenario?.id === scenario.id ? 'border-yellow-500 bg-yellow-50/20 ring-1 ring-yellow-500' : 'border-gray-200 bg-white hover:border-yellow-300'}`}
                >
                  <input type="radio" className="sr-only" name="scenario" value={scenario.id} checked={selectedScenario?.id === scenario.id} onChange={() => setSelectedScenario(scenario)} />
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-lg ${scenario.iconBg}`}>
                      <Icon className={`w-5 h-5 ${scenario.iconColor}`} />
                    </div>
                    <span className="font-semibold text-gray-900">{scenario.name}</span>
                  </div>
                  <p className="text-sm text-gray-500 leading-relaxed">{scenario.description}</p>
                  <div className="space-y-1">
                    {scenario.examples.map((ex, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-xs text-gray-400">
                        <span className="w-1 h-1 rounded-full bg-gray-300 shrink-0" /> {ex}
                      </div>
                    ))}
                  </div>
                </label>
              );
            })}
          </div>
          <div className="flex justify-end">
            <Button onClick={() => setStep(2)} disabled={!canProceedStep1} className="gap-2">
              Next: Test Details →
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Test Details */}
      {step === 2 && (
        <div className="space-y-5">
          <div className="flex items-center gap-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
            {(() => { const Icon = selectedScenario?.icon; return Icon ? <Icon className="w-4 h-4 shrink-0" /> : null; })()}
            <span>Scenario: <strong>{selectedScenario?.name}</strong></span>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 mb-1.5">Test Case Title *</label>
            <input type="text" value={title} onChange={e => setTitle(e.target.value)} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-yellow-500 focus:border-yellow-500" placeholder="e.g., Verify PII block on HR agent upload endpoint" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">Scope *</label>
            <div className="grid grid-cols-3 gap-3">
              {SCOPES.map(s => {
                const Icon = s.icon;
                return (
                  <label key={s.id} className={`flex flex-col items-center gap-2 p-3 rounded-lg border-2 cursor-pointer transition-all text-center ${selectedScope === s.id ? 'border-yellow-500 bg-yellow-50/20' : 'border-gray-200 bg-white hover:border-yellow-300'}`}>
                    <input type="radio" className="sr-only" name="scope" value={s.id} checked={selectedScope === s.id} onChange={() => setSelectedScope(s.id)} />
                    <Icon className="w-5 h-5 text-gray-500" />
                    <span className="text-xs font-semibold text-gray-900">{s.label}</span>
                    <span className="text-[10px] text-gray-400">{s.description}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {selectedScope && (
            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1.5">Scope Target *</label>
              <input type="text" value={scopeTarget} onChange={e => setScopeTarget(e.target.value)} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-yellow-500 focus:border-yellow-500" placeholder={selectedScope === 'scope-agent' ? 'e.g., hr-onboarding-agent-v2' : selectedScope === 'scope-endpoint' ? 'e.g., /api/v1/agents/chat' : 'e.g., pii-detection-v3'} />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-900 mb-1.5">Description * <span className="font-normal text-gray-400">(min 20 chars)</span></label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={4} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-yellow-500 focus:border-yellow-500" placeholder="Describe the exact test steps, what data will be used, and what system components are involved..." />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 mb-1.5">Expected Outcome *</label>
            <input type="text" value={expectedOutcome} onChange={e => setExpectedOutcome(e.target.value)} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-yellow-500 focus:border-yellow-500" placeholder="e.g., Policy blocks request and logs a HIGH severity event" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">Access Expiry Window *</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {EXPIRY_OPTIONS.map(opt => (
                <label key={opt.value} className={`flex flex-col p-3 rounded-lg border-2 cursor-pointer transition-all ${expiry === opt.value ? 'border-yellow-500 bg-yellow-50/20' : 'border-gray-200 bg-white hover:border-yellow-300'}`}>
                  <input type="radio" className="sr-only" name="expiry" value={opt.value} checked={expiry === opt.value} onChange={() => setExpiry(opt.value)} />
                  <span className="font-bold text-sm text-gray-900">{opt.label}</span>
                  <span className="text-[11px] text-gray-500 mt-0.5">{opt.description}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-between pt-2">
            <Button variant="ghost" onClick={() => setStep(1)}>← Back</Button>
            <Button onClick={() => setStep(3)} disabled={!canProceedStep2} className="gap-2">Next: Review →</Button>
          </div>
        </div>
      )}

      {/* Step 3: Review & Confirm */}
      {step === 3 && (
        <div className="space-y-5">
          <h2 className="text-lg font-semibold">Confirm Break Glass Request</h2>

          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <div className="px-5 py-4 bg-gray-50 border-b border-gray-200">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-gray-500" /> Request Summary
              </h3>
            </div>
            <div className="divide-y divide-gray-100">
              {[
                { label: 'Requester', value: `${user?.name} (${user?.email})` },
                { label: 'Scenario', value: selectedScenario?.name },
                { label: 'Title', value: title },
                { label: 'Scope', value: `${SCOPES.find(s => s.id === selectedScope)?.label}: ${scopeTarget}` },
                { label: 'Expected Outcome', value: expectedOutcome },
                { label: 'Expiry Window', value: expiry },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-start px-5 py-3 text-sm gap-4">
                  <span className="text-gray-500 w-36 shrink-0">{label}</span>
                  <span className="font-medium text-gray-900">{value}</span>
                </div>
              ))}
              <div className="px-5 py-3 text-sm">
                <span className="text-gray-500 block mb-1">Description</span>
                <p className="text-gray-800 leading-relaxed">{description}</p>
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 bg-orange-50 border border-orange-200 rounded-lg">
            <Clock className="w-5 h-5 text-orange-500 shrink-0 mt-0.5" />
            <p className="text-sm text-orange-800">
              Upon approval, access will be granted for <strong>{expiry}</strong> and automatically revoked at expiry. All actions taken during this window will be captured in the audit log and linked to this request ID.
            </p>
          </div>

          <div className="space-y-3">
            <label className="flex items-start gap-3 p-4 bg-white border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
              <input type="checkbox" className="mt-0.5 w-4 h-4 text-yellow-500 rounded" checked={acknowledged} onChange={e => setAcknowledged(e.target.checked)} />
              <span className="text-sm text-gray-700">I confirm this is a legitimate, pre-planned test case or emergency access request, and that I have the authority to submit it.</span>
            </label>
            <label className="flex items-start gap-3 p-4 bg-white border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
              <input type="checkbox" className="mt-0.5 w-4 h-4 text-yellow-500 rounded" checked={complianceAck} onChange={e => setComplianceAck(e.target.checked)} />
              <span className="text-sm text-gray-700">I understand this request will be logged, that the Security and Compliance teams will be notified, and that all activity is subject to review.</span>
            </label>
          </div>

          {error && <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>}

          <div className="flex justify-between pt-2">
            <Button variant="ghost" onClick={() => setStep(2)}>← Back</Button>
            <Button onClick={handleSubmit} disabled={!canSubmit} className="gap-2 !bg-yellow-600 hover:!bg-yellow-700">
              {submitting ? 'Submitting...' : '⚡ Submit Break Glass Request'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
