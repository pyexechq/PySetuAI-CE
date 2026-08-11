# Design System

## Overview

HelixGuard AI follows an enterprise SaaS design language inspired by Datadog, Grafana, CrowdStrike, Wiz, and ServiceNow.

## Themes

### Dark (Default)
- Background: `#0b1120`
- Card: `#111827`
- Primary: `#818cf8` (Indigo)
- Sidebar: `#0f172a`

### Light
- Background: `#f8fafc`
- Card: `#ffffff`
- Primary: `#6366f1` (Indigo)
- Sidebar: `#ffffff`

## Typography

- **Headings:** Geist Sans, semibold
- **Body:** Geist Sans, regular
- **Code/Metrics:** Geist Mono, tabular-nums for data

## Color Semantics

| Color | Usage |
|-------|-------|
| Green (`#22c55e`) | Safe, low risk, positive trends |
| Yellow (`#eab308`) | Medium risk, warnings |
| Orange (`#f97316`) | High risk, policy triggers |
| Red (`#ef4444`) | Critical, blocked, destructive |
| Blue (`#3b82f6`) | Primary actions, total metrics |
| Purple (`#8b5cf6`) | MCP-related items |

## Components

### Metric Cards
Large numeric value, trend indicator (% change vs last week), icon badge.

### Data Tables
Clean borders, tabular-nums for numbers, badge components for status/risk.

### Charts
Recharts with theme-aware tooltips. Donut charts for distribution, line charts for time series.

### Navigation
Fixed sidebar with icon + label, active state with primary color background. Collapsible for space efficiency.

### Badges
Rounded-full pills with semantic color variants: default, secondary, destructive, success, warning.

## Layout

```
┌──────────┬──────────────────────────────────────┐
│          │  Header (title, date range, actions)  │
│ Sidebar  ├──────────────────────────────────────┤
│ (256px)  │                                      │
│          │  Main Content (scrollable, p-6)      │
│          │                                      │
└──────────┴──────────────────────────────────────┘
```

## Accessibility

- Semantic HTML elements
- ARIA labels on icon-only buttons
- Color is supplemented with text/icons (not color-only indicators)
- Keyboard navigable sidebar links
- Sufficient contrast ratios in both themes

## Responsive Breakpoints

- Mobile: Sidebar collapsed by default
- Tablet (md): 2-column metric grid
- Desktop (lg): 3-column charts
- Wide (xl): 4-column metric grid
