# ADR-002: Next.js App Router

## Status

Accepted

## Context

The frontend requires server-side rendering capabilities, file-based routing for 13+ modules, and modern React patterns for an enterprise SaaS dashboard.

## Decision

Use Next.js 16 with App Router, TypeScript, and Tailwind CSS v4.

## Alternatives Considered

1. **Pages Router** — Legacy Next.js routing. Rejected in favor of App Router layouts and server components.
2. **Vite + React SPA** — Faster dev experience but lacks SSR, file-based routing, and deployment optimizations.
3. **Remix** — Strong alternative but smaller enterprise component ecosystem for data grids and flow editors.

## Consequences

- Layout-based sidebar/header shared across all module routes
- Server components available for future SSR dashboard data
- shadcn/ui integrates cleanly with App Router
- React 19 features available
