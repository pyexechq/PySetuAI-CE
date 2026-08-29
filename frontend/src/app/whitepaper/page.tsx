"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Shield,
  FileText,
  Download,
  CheckCircle2,
  Lock,
  ArrowRight,
  Server,
  Workflow,
  Cpu,
  Layers,
  Sparkles,
  ChevronRight,
  Printer,
  Share2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { LoginModal } from "@/components/auth/login-modal";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

export default function WhitepaperPage() {
  const [loginOpen, setLoginOpen] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  const handlePrint = () => {
    window.print();
  };

  const handleDownload = () => {
    setDownloaded(true);
    setTimeout(() => {
      window.print();
    }, 400);
  };

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/20">
      <div className="print:hidden">
        <MarketingNav onLoginClick={() => setLoginOpen(true)} />
      </div>

      {/* Hero Header */}
      <section className="relative overflow-hidden border-b border-border/60 bg-gradient-to-b from-primary/5 via-background to-background py-16 md:py-24 print:border-none print:bg-transparent print:py-0 print:pt-4">
        <div className="mx-auto max-w-5xl px-4 print:px-0">
          {/* Printable Corporate Header (visible only on PDF / Print) */}
          <div className="hidden print:block border-b-2 border-primary/80 pb-4 mb-8">
            <div className="flex justify-between items-center text-xs text-muted-foreground">
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded bg-primary/10 text-primary font-bold text-xs">
                  PS
                </div>
                <span className="font-bold text-foreground">PySetu AI — Enterprise Architecture &amp; Research</span>
              </div>
              <span>Doc ID: <strong>WP-2026-MCP-GOV-GA</strong> • Confidential / Public Whitepaper</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-primary print:border print:border-primary/40">
              <FileText className="h-3.5 w-3.5" /> Technical Architecture Whitepaper
            </span>
            <span className="text-muted-foreground">•</span>
            <span className="text-muted-foreground">August 2026 Edition</span>
            <span className="text-muted-foreground">•</span>
            <span className="text-muted-foreground">Version 2.5 GA</span>
          </div>

          <h1 className="mt-4 text-3xl font-extrabold tracking-tight md:text-5xl lg:leading-tight print:text-3xl">
            Governing the Autonomous Digital Enterprise: <br className="hidden md:inline" />
            <span className="bg-gradient-to-r from-primary via-indigo-500 to-sky-500 bg-clip-text text-transparent">
              A 5-Pillar Architecture for Zero-AI Ingress Defense, Sequential MCP Safety, and Cost Arbitrage
            </span>
          </h1>

          <p className="mt-6 text-lg text-muted-foreground md:text-xl print:text-sm">
            A comprehensive architectural blueprint for Enterprise CISOs, Chief Architects, and IT Operations Leaders to deploy, monitor, and enforce least-privilege governance across autonomous AI agents, Model Context Protocol (MCP) ecosystems, and distributed edge nodes.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-border/40 pt-6 print:border-border/60">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 font-bold text-primary print:border print:border-primary">
                PS
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">PySetu AI Architecture &amp; Research Group</p>
                <p className="text-xs text-muted-foreground">In collaboration with Enterprise Security Leaders</p>
              </div>
            </div>

            <div className="flex items-center gap-2 print:hidden">
              <Button variant="outline" size="sm" onClick={handlePrint} className="gap-1.5">
                <Printer className="h-4 w-4" /> Print / Save PDF
              </Button>
              <Button size="sm" onClick={handleDownload} className="gap-1.5 shadow-sm">
                <Download className="h-4 w-4" /> {downloaded ? "Opening PDF View..." : "Download Full PDF"}
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content Layout */}
      <main className="mx-auto max-w-5xl px-4 py-12 print:px-0 print:py-6">
        <div className="grid gap-12 lg:grid-cols-[1fr_260px]">
          {/* Article Body */}
          <article className="prose prose-neutral dark:prose-invert max-w-none space-y-10">
            {/* Executive Summary */}
            <section id="executive-summary" className="scroll-mt-24">
              <h2 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl print:text-xl print:font-bold">
                1. Executive Summary: The Agentic Paradigm Shift
              </h2>
              <p className="text-muted-foreground leading-relaxed print:text-neutral-800">
                Over the past 24 months, enterprise generative AI has evolved from static prompt-response chatbots into <strong>autonomous multi-agent systems</strong>. Agents powered by foundation models (OpenAI, Anthropic Claude, Google Gemini) now actively invoke tools, execute SQL statements, trigger API updates, and orchestrate complex enterprise business logic via the <strong>Model Context Protocol (MCP)</strong>.
              </p>
              <p className="text-muted-foreground leading-relaxed print:text-neutral-800">
                However, existing enterprise security architectures—such as Web Application Firewalls (WAFs), Cloud Access Security Brokers (CASBs), and traditional API Gateways—were designed for deterministic REST transactions. They lack visibility into bidirectional JSON-RPC MCP streams, cannot inspect non-deterministic agent tool-chains, and fail to prevent unauthorized data movement into vector embeddings.
              </p>
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-5 not-prose my-6 break-inside-avoid print:break-inside-avoid print:my-4 print:p-4 print:bg-slate-50 print:border-primary/40">
                <h4 className="font-semibold text-primary flex items-center gap-2">
                  <Shield className="h-5 w-5" /> The Core Thesis of PySetu AI v2.5
                </h4>
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed print:text-neutral-700">
                  Enterprise AI governance requires an inline, sub-millisecond <strong>Zero-AI Control Plane</strong> that sits directly on the live execution path between AI clients and downstream tools. PySetu v2.5 achieves this via a 5-pillar architecture: Sub-Millisecond Pre-Flight Interception (&lt;0.3ms), Sequential MCP State Machine Defense, 100% MITRE ATLAS / OWASP Compliance, Dynamic Cost Arbitrage (slashing token bills by 94%), and a Zero-Hop Distributed Edge Mesh.
                </p>
              </div>
            </section>

            {/* Attack Vectors */}
            <section id="threat-vectors" className="scroll-mt-24 break-inside-avoid print:break-inside-avoid">
              <h2 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl print:text-xl print:font-bold">
                2. Threat Landscape: The 5 Adversarial Pillars of Autonomous AI
              </h2>
              <div className="grid gap-4 not-prose my-6 sm:grid-cols-2 print:grid-cols-2 print:my-3">
                <div className="rounded-xl border border-border/70 bg-card p-4 shadow-sm break-inside-avoid print:break-inside-avoid print:p-3 print:bg-slate-50">
                  <span className="text-xs font-bold uppercase tracking-wider text-red-500">MITRE AML.T0054 / OWASP LLM01</span>
                  <h4 className="mt-1 font-semibold text-foreground print:text-sm">Direct Prompt Injections &amp; Jailbreaks</h4>
                  <p className="mt-1 text-xs text-muted-foreground print:text-neutral-700">
                    Adversarial prompts overriding system directives or forcing model developer mode. PySetu intercepts these in &lt;0.3ms without paying upstream LLM token costs.
                  </p>
                </div>
                <div className="rounded-xl border border-border/70 bg-card p-4 shadow-sm break-inside-avoid print:break-inside-avoid print:p-3 print:bg-slate-50">
                  <span className="text-xs font-bold uppercase tracking-wider text-amber-500">MITRE AML.T0025 / OWASP LLM06</span>
                  <h4 className="mt-1 font-semibold text-foreground print:text-sm">Sequential Tool Exfiltration Chains</h4>
                  <p className="mt-1 text-xs text-muted-foreground print:text-neutral-700">
                    Agents reading sensitive secrets/databases in Step 1 and chaining into outbound HTTP/webhooks in Step 2. PySetu&apos;s state machine halts the chain before egress.
                  </p>
                </div>
                <div className="rounded-xl border border-border/70 bg-card p-4 shadow-sm break-inside-avoid print:break-inside-avoid print:p-3 print:bg-slate-50">
                  <span className="text-xs font-bold uppercase tracking-wider text-blue-500">MITRE AML.T0043 / OWASP LLM02</span>
                  <h4 className="mt-1 font-semibold text-foreground print:text-sm">Sensitive Information Disclosure &amp; Vector Leaks</h4>
                  <p className="mt-1 text-xs text-muted-foreground print:text-neutral-700">
                    Confidential PII, PHI, API keys, or embeddings leaking across tenant boundaries or un-governed vector databases.
                  </p>
                </div>
                <div className="rounded-xl border border-border/70 bg-card p-4 shadow-sm break-inside-avoid print:break-inside-avoid print:p-3 print:bg-slate-50">
                  <span className="text-xs font-bold uppercase tracking-wider text-purple-500">MITRE AML.T0048 / OWASP LLM10</span>
                  <h4 className="mt-1 font-semibold text-foreground print:text-sm">Runaway Loops &amp; Unbounded Financial Exhaustion</h4>
                  <p className="mt-1 text-xs text-muted-foreground print:text-neutral-700">
                    Agents trapped in 3+ identical tool call recursion loops burning enterprise token budgets. Blocked by PySetu&apos;s loop breaker and token quotas.
                  </p>
                </div>
              </div>
            </section>

            {/* Architecture Section */}
            <section id="architecture" className="scroll-mt-24">
              <h2 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl print:text-xl print:font-bold">
                3. The PySetu 5-Pillar Enterprise Architecture
              </h2>
              <p className="text-muted-foreground leading-relaxed print:text-neutral-800">
                PySetu AI operates as a unified, high-performance distributed control plane. The runtime consists of five core micro-architectural pillars:
              </p>

              <div className="space-y-4 not-prose my-6 print:my-3">
                <div className="flex gap-4 rounded-xl border border-border/70 bg-card p-5 break-inside-avoid print:break-inside-avoid print:p-4 print:bg-slate-50">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-500 font-bold print:hidden">
                    <Shield className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground print:text-sm">Pillar 1: Inline Zero-AI Pre-Flight Interceptor (&lt; 0.3 ms)</h4>
                    <p className="mt-1 text-sm text-muted-foreground leading-relaxed print:text-xs print:text-neutral-700">
                      Scans inbound prompts in ~267 microseconds using Unicode NFKD canonicalization and compiled declarative lookup tables. Intercepts attacks before LLM token forwarding, saving 100% of attack token costs.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 rounded-xl border border-border/70 bg-card p-5 break-inside-avoid print:break-inside-avoid print:p-4 print:bg-slate-50">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500 font-bold print:hidden">
                    <Workflow className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground print:text-sm">Pillar 2: Sequential MCP Tool Chain State Machine</h4>
                    <p className="mt-1 text-sm text-muted-foreground leading-relaxed print:text-xs print:text-neutral-700">
                      Tracks agent tool execution history across iterative reasoning loops. Identifies and halts 5 multi-step attack graphs (Exfiltration Chains, RCE, Destructive Mutations, Privilege Escalations, and Infinite Loop Runaways) before execution.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 rounded-xl border border-border/70 bg-card p-5 break-inside-avoid print:break-inside-avoid print:p-4 print:bg-slate-50">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-500 font-bold print:hidden">
                    <CheckCircle2 className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground print:text-sm">Pillar 3: MITRE ATLAS, OWASP GenAI &amp; Automated 10k Nightly Cron</h4>
                    <p className="mt-1 text-sm text-muted-foreground leading-relaxed print:text-xs print:text-neutral-700">
                      100% compliant scoring across 11 standardized adversarial controls with real-time evidence generation. Celery Beat executes nightly 10,000-row golden dataset benchmarks at 02:00 UTC to guarantee regression-free rule updates.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 rounded-xl border border-border/70 bg-card p-5 break-inside-avoid print:break-inside-avoid print:p-4 print:bg-slate-50">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-sky-500/10 text-sky-500 font-bold print:hidden">
                    <Cpu className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground print:text-sm">Pillar 4: Dynamic Cost Arbitrage Engine</h4>
                    <p className="mt-1 text-sm text-muted-foreground leading-relaxed print:text-xs print:text-neutral-700">
                      Analyzes prompt length, code syntax, and reasoning markers to dynamically route simple tasks (translation, summarization, Q&amp;A) to high-efficiency flash models, cutting token spend by 91.7% to 94.0% while preserving frontier models for complex tasks.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 rounded-xl border border-border/70 bg-card p-5 break-inside-avoid print:break-inside-avoid print:p-4 print:bg-slate-50">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-purple-500/10 text-purple-500 font-bold print:hidden">
                    <Layers className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground print:text-sm">Pillar 5: Distributed Edge Mesh &amp; Zero-Hop Wasm Sync</h4>
                    <p className="mt-1 text-sm text-muted-foreground leading-relaxed print:text-xs print:text-neutral-700">
                      Compiles declarative classifier rules, MCP sequence attack graphs, and OPA policies into regional sync bundles for local sub-50μs execution on Envoy/Wasm edge nodes with sub-1ms synchronization latency.
                    </p>
                  </div>
                </div>
              </div>
            </section>

            {/* Enterprise Integration Blueprint */}
            <section id="enterprise-integration" className="scroll-mt-24 break-inside-avoid print:break-inside-avoid">
              <h2 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl print:text-xl print:font-bold">
                4. Enterprise Integration Blueprint (ITSM &amp; AIOps)
              </h2>
              <p className="text-muted-foreground leading-relaxed print:text-neutral-800">
                A critical requirement for enterprise adoption is seamless integration into existing IT Service Management (ITSM) and Security Operations Center (SOC) workflows. PySetu AI natively bridges AI agent actions into ITIL change and incident frameworks:
              </p>
              <ul className="space-y-2 text-sm text-muted-foreground print:text-xs">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-primary mt-0.5" />
                  <span><strong>Automatic ITSM Incident Dispatch</strong>: High-risk policy violations and prompt injection attempts automatically spawn structured incident tickets in <strong>BMC Helix ITSM, ServiceNow, or Jira Service Management</strong>.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-primary mt-0.5" />
                  <span><strong>Change Advisory Board (CAB) Approvals</strong>: Risky MCP tool invocations (e.g. database schema migrations or cloud resource provisioning) trigger multi-stakeholder approval flows in PySetu's Approval Center before execution.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-primary mt-0.5" />
                  <span><strong>Zero-Trust Secret Injection</strong>: Integrates with <strong>HashiCorp Vault and AWS KMS</strong>, dynamically injecting credentials at runtime so developers and agents never hold raw passwords or API keys.</span>
                </li>
              </ul>
            </section>

            {/* Compliance & Audit */}
            <section id="compliance-frameworks" className="scroll-mt-24 break-inside-avoid print:break-inside-avoid">
              <h2 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl print:text-xl print:font-bold">
                5. Compliance Standards &amp; Evidence Generation
              </h2>
              <p className="text-muted-foreground leading-relaxed print:text-neutral-800">
                PySetu AI maps every prompt, response, tool call, and policy decision to international compliance frameworks:
              </p>
              <div className="overflow-x-auto not-prose my-6 break-inside-avoid print:break-inside-avoid print:my-3">
                <table className="w-full text-left text-xs border-collapse border border-border">
                  <thead>
                    <tr className="bg-muted/40 border-b border-border print:bg-slate-100">
                      <th className="p-3 font-semibold print:p-2">Framework</th>
                      <th className="p-3 font-semibold print:p-2">Mandated Control</th>
                      <th className="p-3 font-semibold print:p-2">PySetu Technical Implementation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    <tr className="break-inside-avoid print:break-inside-avoid">
                      <td className="p-3 font-bold text-foreground print:p-2">SOC 2 (Type II)</td>
                      <td className="p-3 text-muted-foreground print:p-2 print:text-neutral-700">CC6.1 / CC6.6 Access &amp; Data Protection</td>
                      <td className="p-3 text-muted-foreground print:p-2 print:text-neutral-700">Granular MCP RBAC, immutable audit logging with client key attribution.</td>
                    </tr>
                    <tr className="break-inside-avoid print:break-inside-avoid">
                      <td className="p-3 font-bold text-foreground print:p-2">HIPAA Security Rule</td>
                      <td className="p-3 text-muted-foreground print:p-2 print:text-neutral-700">§164.312 ePHI Transmission &amp; Integrity</td>
                      <td className="p-3 text-muted-foreground print:p-2 print:text-neutral-700">Streaming real-time PHI redaction and Governed RAG pre-embedding barrier.</td>
                    </tr>
                    <tr className="break-inside-avoid print:break-inside-avoid">
                      <td className="p-3 font-bold text-foreground print:p-2">ISO / IEC 42001</td>
                      <td className="p-3 text-muted-foreground print:p-2 print:text-neutral-700">AI Management System Governance</td>
                      <td className="p-3 text-muted-foreground print:p-2 print:text-neutral-700">Live policy version history, agent inventory tracking, and risk-tier attribution.</td>
                    </tr>
                    <tr className="break-inside-avoid print:break-inside-avoid">
                      <td className="p-3 font-bold text-foreground print:p-2">NIST AI RMF 1.0</td>
                      <td className="p-3 text-muted-foreground print:p-2 print:text-neutral-700">Govern 1.1 / Map 1.5 Risk Tracking</td>
                      <td className="p-3 text-muted-foreground print:p-2 print:text-neutral-700">Multi-hop tool-chain attack surface graph with real-time risk scoring.</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            {/* Conclusion */}
            <section id="conclusion" className="scroll-mt-24">
              <h2 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
                6. Conclusion &amp; Getting Started
              </h2>
              <p className="text-muted-foreground leading-relaxed">
                As autonomous AI agents become core infrastructure in modern enterprises, organizations cannot afford to compromise between developer innovation and strict security governance. PySetu AI bridges this divide—providing developers with a frictionless self-service portal while equipping CISOs with uncompromised, real-time control.
              </p>
              <div className="rounded-2xl border border-border bg-gradient-to-r from-primary/10 via-background to-background p-6 not-prose my-8">
                <h3 className="text-lg font-bold text-foreground">Ready to secure your enterprise AI ecosystem?</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Deploy the open-core community gateway in under 2 minutes or schedule an architectural walkthrough with our enterprise engineering team.
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Button onClick={() => setLoginOpen(true)}>Get Started Free</Button>
                  <Button variant="outline" asChild>
                    <Link href="/developer-portal">Explore Developer Portal ↗</Link>
                  </Button>
                </div>
              </div>
            </section>
          </article>

          {/* Sticky Table of Contents Sidebar */}
          <aside className="hidden lg:block print:hidden">
            <div className="sticky top-24 rounded-xl border border-border/60 bg-card p-4 shadow-sm text-xs">
              <p className="font-bold uppercase tracking-wider text-muted-foreground">Table of Contents</p>
              <nav className="mt-3 space-y-2 text-muted-foreground">
                <a href="#executive-summary" className="block hover:text-primary transition-colors">
                  1. Executive Summary
                </a>
                <a href="#threat-vectors" className="block hover:text-primary transition-colors">
                  2. Threat Landscape (5 Vectors)
                </a>
                <a href="#architecture" className="block hover:text-primary transition-colors">
                  3. Control Plane Architecture
                </a>
                <a href="#enterprise-integration" className="block hover:text-primary transition-colors">
                  4. Enterprise Integration Blueprint
                </a>
                <a href="#compliance-frameworks" className="block hover:text-primary transition-colors">
                  5. Compliance &amp; Standards
                </a>
                <a href="#conclusion" className="block hover:text-primary transition-colors">
                  6. Conclusion &amp; Next Steps
                </a>
              </nav>

              <div className="mt-6 border-t border-border/60 pt-4">
                <p className="font-bold text-foreground">Document Details</p>
                <div className="mt-2 space-y-1.5 text-muted-foreground">
                  <p>Format: <span className="text-foreground">Technical Whitepaper</span></p>
                  <p>Classification: <span className="text-foreground">Public Distribution</span></p>
                  <p>Architecture: <span className="text-foreground">PySetu v2.4 GA</span></p>
                </div>
                <Button size="sm" variant="outline" onClick={handleDownload} className="mt-4 w-full gap-1">
                  <Download className="h-3.5 w-3.5" /> PDF Download
                </Button>
              </div>
            </div>
          </aside>
        </div>
      </main>

      <div className="print:hidden">
        <MarketingFooter />
      </div>
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}
