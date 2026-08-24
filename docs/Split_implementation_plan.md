# Open Core vs. SaaS Architecture Separation

You have requested a strategy to separate the public GitHub repository from the production VPS deployment, explicitly stripping out the **Marketing Site** and **Tenant Admin/Platform Ops controls** from the public repository.

This is a classic "Open Core" packaging problem. To achieve this, the codebase must be physically separated so proprietary code never enters the public `.git` history.

Here are the three industry-standard strategies to achieve this.

## Open Questions

> [!IMPORTANT]
> Which of the following approaches best fits your workflow? I strongly recommend **Option 1**, as it requires the least amount of refactoring right now and keeps your developer experience unified.

---

## Option 1: The "Copybara" / Mirror Script (Recommended)

You maintain a single **Private Repository** (e.g., `PySetuAI-Private`). All your daily work, including the marketing site and SaaS controls, happens here. 

You run an automated CI script (like [Google's Copybara](https://github.com/google/copybara) or a custom GitHub Action using `rsync` and `git-filter-repo`) that automatically pushes to the **Public GitHub Repository** on every merge, *excluding* specific folders.

**What we would exclude in the sync script:**
- `frontend/src/components/marketing/*`
- `frontend/src/app/platform/*`
- `backend/app/api/v1/platform.py`

**Pros:** You get to develop in a single monorepo. No complex cross-repo dependency management.
**Cons:** If the community submits a Pull Request to the public repo, you have to manually port it into your private repo.

## Option 2: Core Submodule Strategy

You split the repository into two physical git repositories:
1. `PySetuAI-Core` (Public on GitHub)
2. `PySetuAI-SaaS` (Private for your VPS)

The `PySetuAI-SaaS` repo includes `PySetuAI-Core` as a **Git Submodule**. The SaaS repo only contains the marketing site, platform API routes, and custom deployment overrides.

**Pros:** Clean separation of concerns. Easy to merge community PRs.
**Cons:** Requires refactoring the Next.js and FastAPI apps to allow "plugins" or overriding routes from an outer wrapper directory. Managing submodules can be frustrating.

## Option 3: Monorepo with Multiple Packages

We refactor the structure to use a package manager like `npm workspaces` / Turborepo and Python sub-packages:
- `packages/core-backend`
- `packages/saas-backend`
- `apps/marketing-site`
- `apps/core-dashboard`

Only the `core` packages are tracked in the public GitHub repo. The `saas` packages are tracked in a private repo or managed via a sparse git checkout.

**Pros:** Excellent scalability for enterprise software.
**Cons:** Very high upfront refactoring cost.

---

## Verification Plan

If you select **Option 1**, I will:
1. Write a `.github/workflows/sync-open-core.yml` script (or bash script) that defines exactly which directories to strip out.
2. Provide instructions on how to change your current `origin` to a private repo, and set the public GitHub as a downstream remote.

Please review the options and let me know how you'd like to proceed!
