import { LegalPageShell } from "@/components/marketing/legal-page-shell";

export default function TermsPage() {
  return (
    <LegalPageShell title="Terms & Conditions" lastUpdated="August 11, 2026">
      <p>
        These Terms & Conditions (&quot;Terms&quot;) govern access to and use of the HelixGuard AI platform,
        websites, and related services (collectively, the &quot;Service&quot;). By using the Service, you agree to
        these Terms.
      </p>

      <h2>1. Service description</h2>
      <p>
        HelixGuard AI provides enterprise AI governance capabilities including LLM routing, MCP governance,
        policy enforcement, observability, and compliance tooling. Features may vary by deployment mode and
        subscription tier.
      </p>

      <h2>2. Accounts and access</h2>
      <p>
        You are responsible for safeguarding credentials issued to your organization. You must notify us promptly
        of any unauthorized access. Tenant administrators control user provisioning within their organization.
      </p>

      <h2>3. Acceptable use</h2>
      <p>
        You agree not to misuse the Service, attempt to bypass security controls, interfere with other tenants, or
        use the Service in violation of applicable law. We may suspend access for violations or security risks.
      </p>

      <h2>4. Data and confidentiality</h2>
      <p>
        Customer data processed through the Service remains subject to your instructions and our Privacy Policy.
        We implement administrative, technical, and organizational measures designed to protect tenant data.
      </p>

      <h2>5. Intellectual property</h2>
      <p>
        HelixGuard AI and its licensors retain all rights in the Service, documentation, and branding. You retain
        ownership of your content and configuration data submitted to the Service.
      </p>

      <h2>6. Disclaimer and limitation of liability</h2>
      <p>
        The Service is provided on an &quot;as is&quot; and &quot;as available&quot; basis to the extent permitted by law. Our
        aggregate liability arising from the Service is limited to fees paid by you in the twelve months preceding
        the claim, unless otherwise required by applicable law.
      </p>

      <h2>7. Changes</h2>
      <p>
        We may update these Terms from time to time. Material changes will be communicated through the Service or
        by email where appropriate. Continued use after changes become effective constitutes acceptance.
      </p>

      <h2>8. Contact</h2>
      <p>
        For questions about these Terms, contact{" "}
        <a href="mailto:legal@helixguard.com">legal@helixguard.com</a>.
      </p>
    </LegalPageShell>
  );
}
