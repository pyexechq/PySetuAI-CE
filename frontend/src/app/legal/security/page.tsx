import { LegalPageShell } from "@/components/marketing/legal-page-shell";

export default function LegalSecurityPage() {
  return (
    <LegalPageShell title="Security & Trust" lastUpdated="August 11, 2026">
      <p>
        PySetu AI is designed for regulated enterprises. Security is embedded across authentication, tenant
        isolation, policy enforcement, and auditability.
      </p>

      <h2>Platform security</h2>
      <ul>
        <li>Multi-tenant isolation with role-based access control (RBAC).</li>
        <li>Encrypted transport (TLS) for data in transit.</li>
        <li>Rate limiting and authentication protections on sensitive endpoints.</li>
        <li>Tamper-evident audit logging for governance and compliance workflows.</li>
      </ul>

      <h2>Operational practices</h2>
      <p>
        We follow secure development practices, dependency monitoring, and controlled release processes. On-premises
        deployments can run entirely within customer-controlled infrastructure.
      </p>

      <h2>Reporting vulnerabilities</h2>
      <p>
        If you believe you have discovered a security issue, please report it responsibly to{" "}
        <a href="mailto:security@pysetu.com">security@pysetu.com</a>. Do not publicly disclose issues until
        we have had a reasonable opportunity to investigate and remediate.
      </p>
    </LegalPageShell>
  );
}
