import { LegalPageShell } from "@/components/marketing/legal-page-shell";

export default function PrivacyPage() {
  return (
    <LegalPageShell title="Privacy Policy" lastUpdated="August 11, 2026">
      <p>
        This Privacy Policy explains how PySetu AI (&quot;PySetu&quot;, &quot;we&quot;, &quot;us&quot;) collects, uses, and
        protects personal information when you visit our marketing site or use our platform.
      </p>

      <h2>Information we collect</h2>
      <ul>
        <li>Account details such as name, email address, role, and tenant affiliation.</li>
        <li>Usage and audit metadata generated when you interact with governed AI workloads.</li>
        <li>Technical data such as IP address, browser type, and device identifiers for security and diagnostics.</li>
      </ul>

      <h2>How we use information</h2>
      <ul>
        <li>Provide, secure, and improve the Service.</li>
        <li>Authenticate users and enforce role-based access controls.</li>
        <li>Generate audit trails, compliance reports, and operational telemetry.</li>
        <li>Respond to support requests and legal obligations.</li>
      </ul>

      <h2>Data retention</h2>
      <p>
        We retain information for as long as necessary to deliver the Service, meet contractual obligations, and
        comply with legal requirements. Audit and compliance records may be retained according to your organization&apos;s
        configured retention policies.
      </p>

      <h2>Sharing and subprocessors</h2>
      <p>
        We do not sell personal information. We may share data with infrastructure providers and subprocessors that
        help us operate the Service, subject to contractual safeguards. We may also disclose information when required
        by law.
      </p>

      <h2>Your rights</h2>
      <p>
        Depending on your jurisdiction, you may have rights to access, correct, delete, or restrict processing of
        your personal information. Contact your tenant administrator or{" "}
        <a href="mailto:hello@pysetu.io">hello@pysetu.io</a> to submit a request.
      </p>

      <h2>International transfers</h2>
      <p>
        Where data is transferred across borders, we apply appropriate safeguards consistent with applicable privacy
        regulations and customer agreements.
      </p>

      <h2>Contact</h2>
      <p>
        Privacy inquiries: <a href="mailto:hello@pysetu.io">hello@pysetu.io</a>
      </p>
    </LegalPageShell>
  );
}
