/** Dev-only login hints — set via NEXT_PUBLIC_* at build time (see docker-compose.yml). */

export const DEMO_LOGIN_HINTS_ENABLED =
  process.env.NEXT_PUBLIC_DEMO_LOGIN_HINTS === "true";

export const DEMO_LOGIN_DEFAULT_EMAIL =
  DEMO_LOGIN_HINTS_ENABLED ? (process.env.NEXT_PUBLIC_DEMO_LOGIN_EMAIL ?? "") : "";

export const DEMO_LOGIN_DEFAULT_PASSWORD =
  DEMO_LOGIN_HINTS_ENABLED ? (process.env.NEXT_PUBLIC_DEMO_LOGIN_PASSWORD ?? "") : "";

export const DEMO_LOGIN_DEFAULT_TENANT =
  DEMO_LOGIN_HINTS_ENABLED ? (process.env.NEXT_PUBLIC_DEMO_LOGIN_TENANT ?? "acme") : "acme";

export function demoLoginHintText(): string | null {
  if (!DEMO_LOGIN_HINTS_ENABLED) return null;
  const email = DEMO_LOGIN_DEFAULT_EMAIL.trim();
  const password = DEMO_LOGIN_DEFAULT_PASSWORD.trim();
  const tenant = DEMO_LOGIN_DEFAULT_TENANT.trim() || "acme";
  if (!email || !password) return null;
  return `Demo: ${email} / ${password} (tenant: ${tenant})`;
}
