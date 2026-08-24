"use client";

import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useState, useRef, useEffect } from 'react';
import {
  LayoutDashboard, KeyRound, FlaskConical, Package, ClipboardList,
  ShieldAlert, Flame, Menu, X, LogOut, Settings, ArrowLeft,
  ChevronDown, ShoppingCart, Terminal, Shield, ExternalLink, Sparkles
} from 'lucide-react';
import { PortalProvider, usePortalContext } from './context';
import { CartDrawer } from '@/components/developer-portal/CartDrawer';
import { useAuthStore } from '@/stores/auth-store';

const NAV_ITEMS = [
  { href: '/developer-portal/dashboard',     label: 'Dashboard',          icon: LayoutDashboard, color: 'text-blue-600',    bg: 'bg-blue-50' },
  { href: '/developer-portal/api-keys',      label: 'API Keys',           icon: KeyRound,        color: 'text-violet-600',  bg: 'bg-violet-50' },
  { href: '/developer-portal/playground',    label: 'Agent Playground',   icon: FlaskConical,    color: 'text-emerald-600', bg: 'bg-emerald-50' },
  { href: '/developer-portal/catalogue',     label: 'Tool Catalogue',     icon: Package,         color: 'text-orange-600',  bg: 'bg-orange-50' },
  { href: '/developer-portal/requests',      label: 'My Requests',        icon: ClipboardList,   color: 'text-sky-600',     bg: 'bg-sky-50' },
  { href: '/developer-portal/dlp-exception', label: 'DLP Exception',      icon: ShieldAlert,     color: 'text-amber-600',   bg: 'bg-amber-50' },
  { href: '/developer-portal/break-glass',   label: 'Break Glass',        icon: Flame,           color: 'text-rose-600',    bg: 'bg-rose-50' },
];

// ─── User Avatar Dropdown ────────────────────────────────────────────────────
function UserMenu() {
  const { user, logout } = useAuthStore();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const initials = user?.name
    ? user.name.split(' ').filter(Boolean).map((n: string) => n[0]).join('').substring(0, 2).toUpperCase()
    : (user?.email?.[0] ?? 'U').toUpperCase();

  const roleLabel = user?.role?.replace(/_/g, ' ') ?? 'developer';

  return (
    <div className="relative flex items-center" ref={ref}>
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2.5 p-1 rounded-full hover:bg-slate-100 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white font-bold text-xs select-none shadow-sm">
          {initials}
        </div>
        <div className="hidden sm:block text-left leading-tight">
          <p className="text-xs font-bold text-slate-900 max-w-[130px] truncate">{user?.name ?? user?.email ?? 'User'}</p>
          <p className="text-[11px] text-slate-500 capitalize">{roleLabel}</p>
        </div>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-64 rounded-2xl border border-slate-200 bg-white shadow-xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
          {/* Profile strip */}
          <div className="px-4 py-3.5 bg-gradient-to-br from-indigo-50/80 via-slate-50 to-violet-50/60 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white font-bold text-sm shadow-sm shrink-0">
                {initials}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-slate-900 truncate">{user?.name ?? 'User'}</p>
                <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                <span className="mt-1 inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-100/80 text-indigo-700 capitalize">
                  {roleLabel}
                </span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="p-1.5 space-y-0.5">
            <Link
              href="/"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <ArrowLeft className="w-4 h-4 text-slate-400" />
              Back to Platform
            </Link>
            <Link
              href="/settings"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <Settings className="w-4 h-4 text-slate-400" />
              Account Settings
            </Link>
            <div className="h-px bg-slate-100 my-1" />
            <button
              onClick={() => { setOpen(false); logout(); router.replace('/login'); }}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-rose-600 hover:bg-rose-50 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Top Header ─────────────────────────────────────────────────────────────
function PortalHeader({ onMenuToggle }: { onMenuToggle: () => void }) {
  const { environment, setEnvironment, cart, setIsCartOpen } = usePortalContext();

  return (
    <header className="h-14 bg-white border-b border-slate-200/80 flex items-center justify-between px-4 lg:px-6 shrink-0 z-20 shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
      {/* Left */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="md:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Logo */}
        <Link href="/developer-portal/dashboard" className="flex items-center gap-2.5 group">
          <div className="h-8 w-8 bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-800 rounded-xl flex items-center justify-center shadow-sm group-hover:scale-105 transition-transform">
            <Terminal className="w-4 h-4 text-white" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-extrabold text-slate-900 text-base tracking-tight">PySetu</span>
            <span className="text-[11px] font-bold px-1.5 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-100">
              DevPortal
            </span>
          </div>
        </Link>

        {/* Back link */}
        <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-slate-200">
          <Link
            href="/"
            className="flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-indigo-600 transition-colors"
          >
            <ArrowLeft className="w-3 h-3" />
            Back to Platform
          </Link>
        </div>
      </div>

      {/* Center — environment switcher */}
      <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200/60 text-xs font-semibold">
        {(['Development', 'Staging', 'Production'] as const).map(env => {
          const isActive = environment === env;
          return (
            <button
              key={env}
              onClick={() => setEnvironment(env)}
              className={`px-3 py-1 rounded-lg transition-all text-xs font-medium whitespace-nowrap ${
                isActive
                  ? 'bg-white shadow-sm text-indigo-700 font-bold border border-slate-200/50'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-200/50'
              }`}
            >
              {env === 'Development' ? 'Dev' : env}
            </button>
          );
        })}
      </div>

      {/* Right — cart + user */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setIsCartOpen(true)}
          className="relative p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-colors"
          aria-label="Open request cart"
        >
          <ShoppingCart className="w-5 h-5" />
          {cart.length > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-600 text-[9px] font-extrabold text-white shadow-sm">
              {cart.length}
            </span>
          )}
        </button>
        <UserMenu />
      </div>
    </header>
  );
}

// ─── Sidebar Nav ─────────────────────────────────────────────────────────────
function SidebarContent({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <div className="flex flex-col h-full">
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {NAV_ITEMS.map(item => {
          const isActive = pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={`group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                isActive
                  ? 'bg-indigo-50/90 text-indigo-700 font-bold shadow-xs'
                  : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900'
              }`}
            >
              <div className={`flex h-8 w-8 items-center justify-center rounded-lg shrink-0 transition-colors ${
                isActive ? item.bg : 'bg-slate-100 group-hover:bg-slate-200/70'
              }`}>
                <Icon className={`h-4 w-4 ${isActive ? item.color : 'text-slate-500 group-hover:text-slate-800'}`} />
              </div>
              <span className="truncate">{item.label}</span>
              {isActive && (
                <span className="ml-auto h-2 w-2 rounded-full bg-indigo-600 shadow-sm" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Sidebar Footer Card */}
      <div className="p-3 border-t border-slate-200/80">
        <div className="p-3 bg-gradient-to-br from-indigo-50 via-slate-50 to-violet-50 rounded-xl border border-indigo-100/80">
          <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-900 mb-1">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>AI Governance</span>
          </div>
          <p className="text-[11px] text-slate-500 leading-snug">
            All agent invocations are guarded by real-time DLP & RBAC policies.
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Layout Shell ─────────────────────────────────────────────────────────────
function PortalLayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { isAuthenticated } = useAuthStore();
  const { portalEnabled, loading } = usePortalContext();

  // Auth guard
  useEffect(() => {
    if (!isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isAuthenticated, pathname, router]);

  if (!isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  // Disabled Tenant Portal Guard
  if (!loading && !portalEnabled) {
    return (
      <div className="flex flex-col h-screen bg-slate-50 text-slate-900 antialiased">
        <header className="h-14 border-b border-slate-200/80 bg-white/95 px-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 bg-slate-800 rounded-xl flex items-center justify-center">
              <Terminal className="w-4 h-4 text-white" />
            </div>
            <span className="font-extrabold text-slate-900 text-base tracking-tight">PySetu DevPortal</span>
          </div>
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-indigo-600 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Platform
          </Link>
        </header>

        <div className="flex-1 flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200 p-8 text-center shadow-xl shadow-slate-100">
            <div className="mx-auto w-14 h-14 rounded-2xl bg-amber-50 border border-amber-200/60 flex items-center justify-center text-amber-600 mb-4">
              <ShieldAlert className="w-7 h-7" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 mb-2">Developer Portal Disabled</h2>
            <p className="text-sm text-slate-600 leading-relaxed mb-6">
              Self-service MCP Developer Portal access has been disabled by your organization administrator for this tenant.
            </p>
            <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-200 text-xs text-slate-500 mb-6 text-left space-y-1">
              <p className="font-semibold text-slate-700">Need access?</p>
              <p>Contact your platform administrator or security team to re-enable portal access in <span className="font-mono text-indigo-600">Platform Settings</span>.</p>
            </div>
            <div className="flex flex-col gap-2">
              <Link
                href="/"
                className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm transition-colors text-center"
              >
                Return to Platform Dashboard
              </Link>
              <Link
                href="/mcp-governance?tab=settings"
                className="w-full py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-colors text-center"
              >
                Open Admin Settings (Admins only)
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-50 text-slate-900 antialiased">
      <PortalHeader onMenuToggle={() => setMobileOpen(v => !v)} />

      <div className="flex flex-1 overflow-hidden">
        {/* ── Desktop Sidebar ── */}
        <aside className="hidden md:flex flex-col w-60 bg-white border-r border-slate-200/80 shrink-0">
          <SidebarContent pathname={pathname} />
        </aside>

        {/* ── Mobile Sidebar Overlay ── */}
        {mobileOpen && (
          <div className="fixed inset-0 z-40 flex md:hidden">
            <div
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
            />
            <div className="relative flex flex-col w-64 h-full bg-white shadow-2xl animate-in slide-in-from-left duration-200">
              <div className="flex items-center justify-between h-14 px-4 border-b border-slate-200">
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 bg-indigo-600 rounded-lg flex items-center justify-center">
                    <Terminal className="w-3.5 h-3.5 text-white" />
                  </div>
                  <span className="font-bold text-slate-900">PySetu DevPortal</span>
                </div>
                <button onClick={() => setMobileOpen(false)} className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <SidebarContent pathname={pathname} onNavigate={() => setMobileOpen(false)} />
            </div>
          </div>
        )}

        {/* ── Main Content ── */}
        <main className="flex-1 overflow-y-auto bg-slate-50/70">
          <div className="p-6 lg:p-8 max-w-6xl mx-auto">
            {children}
          </div>
        </main>
      </div>

      <CartDrawer />
    </div>
  );
}

export default function DeveloperPortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <PortalProvider>
      <PortalLayoutContent>{children}</PortalLayoutContent>
    </PortalProvider>
  );
}
