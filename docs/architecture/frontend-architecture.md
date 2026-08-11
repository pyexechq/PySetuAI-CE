# Frontend Architecture

## Stack

- **Framework:** Next.js 16 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS v4 + CSS variables for theming
- **Components:** shadcn/ui (Radix primitives)
- **Charts:** Recharts
- **State:** Zustand (auth, tenant) + TanStack Query (server state)
- **Future:** React Flow (Policy Studio), AG Grid (Audit Explorer), D3.js (advanced viz)

## Directory Structure

```
frontend/src/
├── app/                    # App Router pages
│   ├── layout.tsx          # Root layout with providers
│   ├── page.tsx            # Executive Dashboard
│   ├── ai-gateway/         # Module pages
│   ├── policy-studio/
│   └── ...
├── components/
│   ├── ui/                 # shadcn/ui primitives
│   ├── layout/             # AppShell, Sidebar, Header
│   └── dashboard/          # Dashboard-specific components
├── config/
│   └── navigation.ts       # Sidebar nav items
├── lib/
│   ├── utils.ts            # cn(), formatters
│   └── mock-data.ts        # Demo data (temporary)
├── providers/
│   ├── theme-provider.tsx
│   └── query-provider.tsx
└── stores/
    ├── auth-store.ts
    └── tenant-store.ts
```

## Design System

- **Theme:** Dark default, light supported via `next-themes`
- **Colors:** Indigo primary, semantic colors for risk levels
- **Typography:** Geist Sans (headings/body), Geist Mono (code)
- **Layout:** Fixed sidebar + scrollable main content area
- **Inspiration:** Datadog, Grafana, CrowdStrike, Wiz

## Routing

Each major module has a dedicated route under `app/`. Module placeholders indicate planned phase.

## State Management

| Store | Purpose | Persistence |
|-------|---------|-------------|
| auth-store | User, token, role | localStorage (Zustand persist) |
| tenant-store | Current tenant, tenant list | Memory |
| TanStack Query | API data (metrics, audit logs) | Cache with staleTime |

## API Integration (Planned)

```typescript
// lib/api.ts — fetch wrapper with JWT + tenant headers
const API_BASE = process.env.NEXT_PUBLIC_API_URL;
```

Dashboard will migrate from `mock-data.ts` to TanStack Query hooks calling `/api/v1/dashboard/metrics`.
