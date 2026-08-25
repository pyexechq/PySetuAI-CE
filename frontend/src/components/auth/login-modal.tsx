"use client";

import { AppModal } from "@/components/ui/dialog";
import { TenantLoginPanel } from "@/components/auth/tenant-login-panel";

interface LoginModalProps {
  open: boolean;
  onClose: () => void;
  tenantSlug?: string;
  lockTenant?: boolean;
  title?: string;
  description?: string;
  redirectTo?: string;
}

export function LoginModal({
  open,
  onClose,
  tenantSlug = "acme",
  lockTenant = false,
  title = "Sign in to PySetu",
  description = "Access your tenant workspace with email and password.",
  redirectTo,
}: LoginModalProps) {
  if (!open) return null;

  return (
    <AppModal title={title} description={description} onClose={onClose} size="sm">
        <TenantLoginPanel
          initialTenantSlug={tenantSlug}
          showTenantField={!lockTenant}
          showDemoHints={!lockTenant}
          submitLabel="Sign in"
          redirectTo={redirectTo}
          onSuccess={onClose}
        />
    </AppModal>
  );
}
