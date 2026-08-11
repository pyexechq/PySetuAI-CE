"use client";

import { useState } from "react";
import { Shield } from "lucide-react";
import { cn } from "@/lib/utils";

interface BrandingLogoProps {
  logoUrl?: string | null;
  alt: string;
  className?: string;
  iconClassName?: string;
}

export function BrandingLogo({ logoUrl, alt, className, iconClassName }: BrandingLogoProps) {
  const [failed, setFailed] = useState(false);

  if (logoUrl && !failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={logoUrl}
        alt={alt}
        className={cn("h-full w-full rounded-lg object-contain", className)}
        onError={() => setFailed(true)}
      />
    );
  }

  return <Shield className={cn("h-5 w-5 text-primary-foreground", iconClassName)} />;
}
