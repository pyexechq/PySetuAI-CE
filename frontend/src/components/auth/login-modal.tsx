"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TenantLoginPanel } from "@/components/auth/tenant-login-panel";

interface LoginModalProps {
  open: boolean;
  onClose: () => void;
  tenantSlug?: string;
  lockTenant?: boolean;
  title?: string;
  description?: string;
}

export function LoginModal({
  open,
  onClose,
  tenantSlug = "acme",
  lockTenant = false,
  title = "Sign in to HelixGuard",
  description = "Access your tenant workspace with email and password.",
}: LoginModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        aria-label="Close sign-in dialog"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">{title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          </div>
          <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>
        <TenantLoginPanel
          initialTenantSlug={tenantSlug}
          showTenantField={!lockTenant}
          showDemoHints={!lockTenant}
          submitLabel="Sign in"
          onSuccess={onClose}
        />
      </div>
    </div>
  );
}
