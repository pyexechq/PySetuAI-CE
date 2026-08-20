# Frontend Agent Handoff

**Last Updated:** Aug 20, 2026

## Work Completed (Aug 20 — Sprint 24)

- **Governance Sandbox Policy Dry Run** — API key selector (`use-client-api-keys.ts`), real-time evaluation (300 ms debounce) against the selected key's bundle, active-rule highlighting (green=passed, red=block, amber=redact, blue=alert, gray=disabled), triggered-rule progress bar
- **`usePolicyRules`** — supports `bundleId`/`defaultBundle`; loads bundle rules for the selected API key
- **Data Protection Center tabs** — DLP scanner (`dlp-scanner-tab.tsx`), movement policy (`data-movement-policy-panel.tsx`), exemptions; `api.scanDataProtectionContent` → `POST /data-protection/scan`
- **API client** — `getPolicyRules` accepts `bundleId`/`defaultBundle`; `testPolicyRules` accepts `api_key_id`/`bundle_id`; added `ApiPolicyPolicyRuleEvaluationResult`

## Work Completed (Aug 15 — Compliance UX)

- **Compliance Center** — tabbed hub (`?tab=frameworks|evidence|exemptions`), KPI row, framework overview chart, quick links
- **IaC evidence** — configure modal (`iac-evidence-config-modal.tsx`), icon header actions on panel
- **GenAI DLP evidence** — data-movement policy modal; quick links (Governed RAG, DLP, Vector store, Break-glass); **not** Policy Studio for movement rules
- **Reports** — preview modal, catalog sparklines, icon actions, recent-generated strip
- **AI metric insights** — `use-metric-insight.ts` on Dashboard, Monitoring, Reports, Compatibility Center
- **Help** — chat widget/layer, guide articles, slug alias normalization
- **Settings** — Integrations default tab Secrets & Vault; updated Vault status copy

Detail: [aug-15-compliance-ux-update.md](../progress/aug-15-compliance-ux-update.md)

## Work Completed (UAG)

- **Compatibility Center** at `/compatibility-center` — model mappings, stats, compatibility scores, provider translation policies
- **Studio Translation Simulator** tab — preview OpenAI → canonical → translated request pipeline
- **Dashboard UAG KPIs** — protocol translations, provider migrations, cost savings, legacy compatibility + route chart
- **Audit Explorer translation trace** — row selection shows source protocol → governance → target provider pipeline
- **Audit Explorer routing rule** — grid column + selected-row badge show the LLM Router rule from `matched_routing_rule`
- Navigation entry and RBAC route for `security_admin`
- API client methods: `listUagMappings`, `createUagMapping`, `deleteUagMapping`, `getUagStats`, `simulateUagTranslation`, `listUagPolicies`, `createUagPolicy`

## Key Files (Aug 15)

```text
frontend/src/components/compliance/compliance-center-view.tsx
frontend/src/components/compliance/compliance-framework-overview.tsx
frontend/src/components/compliance/iac-evidence-config-modal.tsx
frontend/src/components/compliance/data-movement-policy-modal.tsx
frontend/src/components/compliance/genai-evidence-panel.tsx
frontend/src/components/reports/report-preview-modal.tsx
frontend/src/components/reports/report-catalog-table.tsx
frontend/src/hooks/use-metric-insight.ts
frontend/src/components/help/help-chat-widget.tsx
frontend/src/config/help-resources.ts
```

## Next Recommended Tasks

1. Policy edit/delete UI for translation policies
2. Cost savings KPI wired to real billing data when available
3. S6-08: strip demo credentials from production frontend bundles
