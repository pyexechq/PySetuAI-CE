"use client";

import { useState, useRef, useEffect } from "react";

import { Moon, Sun, LogOut, Settings, Menu } from "lucide-react";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { TooltipProvider } from "@/components/ui/tooltip";
import { DateRangePicker } from "@/components/layout/date-range-picker";
import { HeaderHelpMenu } from "@/components/layout/header-help-menu";
import { NotificationCenter } from "@/components/layout/notification-center";
import { PlatformStatusBadge } from "@/components/layout/platform-status-badge";
import { useAuthStore } from "@/stores/auth-store";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { UserPreferencesModal } from "@/components/layout/user-preferences-modal";

interface HeaderProps {
  title: string;
  description?: string;
  onMenuClick?: () => void;
}

export function Header({ title, description, onMenuClick }: HeaderProps) {
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isPreferencesOpen, setIsPreferencesOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setIsProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <TooltipProvider delayDuration={200}>
    <header className="relative z-40 flex h-16 shrink-0 items-center justify-between gap-2 border-b border-border bg-background/80 px-4 backdrop-blur-sm md:px-6">
      <div className="flex min-w-0 items-center gap-2">
        {onMenuClick && (
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={onMenuClick}
            aria-label="Open navigation menu"
          >
            <Menu className="h-5 w-5" />
          </Button>
        )}
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold text-foreground">{title}</h1>
          {description && (
            <p className="hidden truncate text-sm text-muted-foreground sm:block">{description}</p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1 sm:gap-2">
        <DateRangePicker />
        <NotificationCenter />
        <HeaderHelpMenu />
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          data-help-id="header-theme"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label="Toggle theme"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>
        <PlatformStatusBadge />

        <div className="ml-2 flex items-center border-l border-border pl-4 relative" ref={profileRef} data-help-id="header-profile">
          <button
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            className="flex items-center gap-2 rounded-full ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            aria-label="User profile menu"
            aria-expanded={isProfileOpen}
          >
            <Avatar className="h-9 w-9 shrink-0 hover:opacity-90 transition-opacity">
              <AvatarFallback className="bg-primary/20 text-primary font-medium">
                {user?.name?.charAt(0) ?? "A"}
              </AvatarFallback>
            </Avatar>
          </button>
          
          {isProfileOpen && (
            <div className="absolute right-0 top-full mt-2 w-56 rounded-md border border-border bg-popover text-popover-foreground shadow-md animate-in fade-in-80 zoom-in-95">
              <div className="flex flex-col space-y-1 p-3 border-b border-border">
                <p className="text-sm font-medium leading-none truncate">{user?.name}</p>
                <p className="text-xs text-muted-foreground capitalize leading-none mt-1 truncate">
                  {user?.role?.replace("_", " ")}
                </p>
              </div>
              <div className="p-1 space-y-1 mt-1">
                <button
                  onClick={() => { setIsPreferencesOpen(true); setIsProfileOpen(false); }}
                  className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted cursor-pointer transition-colors"
                >
                  <Settings className="h-4 w-4 shrink-0" />
                  Preferences
                </button>
                <button
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-destructive hover:bg-destructive/10 hover:text-destructive cursor-pointer transition-colors"
                >
                  <LogOut className="h-4 w-4 shrink-0" />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      <UserPreferencesModal 
        isOpen={isPreferencesOpen} 
        onClose={() => setIsPreferencesOpen(false)} 
        user={user} 
      />
    </header>
    </TooltipProvider>
  );
}
