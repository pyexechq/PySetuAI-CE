import { LegalPageShell } from "@/components/marketing/legal-page-shell";

export default function CookiesPage() {
  return (
    <LegalPageShell title="Cookie Policy" lastUpdated="August 11, 2026">
      <p>
        This Cookie Policy describes how HelixGuard AI uses cookies and similar technologies on our marketing site
        and authenticated application.
      </p>

      <h2>What are cookies?</h2>
      <p>
        Cookies are small text files stored on your device. They help websites remember preferences, maintain secure
        sessions, and understand how features are used.
      </p>

      <h2>Cookies we use</h2>
      <ul>
        <li>
          <strong>Essential cookies</strong> — required for authentication, session management, and security controls.
        </li>
        <li>
          <strong>Preference cookies</strong> — remember settings such as theme or locale where supported.
        </li>
        <li>
          <strong>Analytics cookies</strong> — help us understand product usage in aggregate when enabled by your
          deployment.
        </li>
      </ul>

      <h2>Managing cookies</h2>
      <p>
        Most browsers let you block or delete cookies. Blocking essential cookies may prevent you from signing in or
        using protected areas of the Service.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about this policy: <a href="mailto:privacy@helixguard.com">privacy@helixguard.com</a>
      </p>
    </LegalPageShell>
  );
}
