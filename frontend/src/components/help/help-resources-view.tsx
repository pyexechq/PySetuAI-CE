"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen, ChevronRight, Clock, LifeBuoy, Mail } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  HELP_GETTING_STARTED,
  HELP_GUIDES,
  HELP_GUIDE_ICONS,
  HELP_POLICIES,
  HELP_SUPPORT_EMAIL,
  HELP_TABS,
  helpGuideArticleHref,
  type HelpTab,
} from "@/config/help-resources";
import { SectionHeading, SectionTabBar } from "@/components/shared/section-chrome";

export function HelpResourcesView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedTab = (searchParams.get("tab") as HelpTab | null) ?? "getting-started";
  const activeTab = HELP_TABS.some((tab) => tab.id === requestedTab) ? requestedTab : "getting-started";
  const [tab, setTab] = useState<HelpTab>(activeTab);

  useEffect(() => {
    setTab(activeTab);
  }, [activeTab]);

  function selectTab(next: HelpTab) {
    setTab(next);
    router.replace(`/help?tab=${next}`, { scroll: false });
  }

  return (
    <div className="space-y-8">
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <LifeBuoy className="h-5 w-5 text-primary" />
            Help & resources
          </CardTitle>
          <CardDescription>
            Onboarding steps, product guides, and trust policies for your PySetu AI tenant workspace.
          </CardDescription>
        </CardHeader>
      </Card>

      <SectionTabBar tabs={HELP_TABS} active={tab} onChange={selectTab} />

      {tab === "getting-started" && (
        <section className="space-y-4">
          <SectionHeading title="First steps" />
          <div className="grid gap-4 md:grid-cols-2">
            {HELP_GETTING_STARTED.map((item) => (
              <Link
                key={item.step}
                href={helpGuideArticleHref(item.articleSlug)}
                className="group rounded-xl border border-border/60 bg-card/50 p-5 transition-colors hover:border-border hover:bg-card"
              >
                <p className="text-xs font-semibold uppercase tracking-wide text-primary">Step {item.step}</p>
                <p className="mt-2 font-medium text-foreground group-hover:text-primary">{item.title}</p>
                <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
                <span className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary">
                  Read guide
                  <ChevronRight className="h-3.5 w-3.5" />
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {tab === "guides" && (
        <section className="space-y-4">
          <SectionHeading title="Knowledge base" />
          <p className="text-sm text-muted-foreground">
            How-to articles for each product area. Open a guide to learn workflows, then jump to the live module when
            you are ready.
          </p>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {HELP_GUIDES.map((guide) => {
              const Icon = HELP_GUIDE_ICONS[guide.icon];
              return (
                <Link
                  key={guide.slug}
                  href={helpGuideArticleHref(guide.slug)}
                  className="group rounded-xl border border-border/60 bg-card/50 p-5 transition-colors hover:border-border hover:bg-card"
                >
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-muted p-2">
                      <Icon className="h-4 w-4 text-muted-foreground group-hover:text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-foreground group-hover:text-primary">{guide.label}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{guide.description}</p>
                      <p className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <BookOpen className="h-3 w-3" />
                        Article
                        <span aria-hidden="true">·</span>
                        <Clock className="h-3 w-3" />
                        {guide.readMinutes} min
                      </p>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      {tab === "policies" && (
        <section className="space-y-6">
          <div className="space-y-4">
            <SectionHeading title="Legal & trust" />
            <div className="grid gap-4 sm:grid-cols-2">
              {HELP_POLICIES.map((policy) => {
                const Icon = policy.icon;
                return (
                  <Link
                    key={policy.href}
                    href={policy.href}
                    className="group rounded-xl border border-border/60 bg-card/50 p-5 transition-colors hover:border-border hover:bg-card"
                  >
                    <div className="flex items-start gap-3">
                      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground group-hover:text-primary" />
                      <div>
                        <p className="font-medium text-foreground group-hover:text-primary">{policy.label}</p>
                        <p className="mt-1 text-sm text-muted-foreground">{policy.description}</p>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>

          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Mail className="h-4 w-4" />
                Need more help?
              </CardTitle>
              <CardDescription>
                For security issues or enterprise support requests, contact{" "}
                <a href={`mailto:${HELP_SUPPORT_EMAIL}`} className="font-medium text-primary hover:underline">
                  {HELP_SUPPORT_EMAIL}
                </a>
                .
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Include your tenant slug, affected module, and steps to reproduce when reporting an issue.
            </CardContent>
          </Card>
        </section>
      )}
    </div>
  );
}
