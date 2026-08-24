"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BookOpen, Calendar, Clock, FileText, Loader2, Sparkles } from "lucide-react";
import { BLOG_CATEGORIES } from "@/lib/blog";
import { api, type ApiBlogArticle } from "@/lib/api";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { LoginModal } from "@/components/auth/login-modal";
import { cn } from "@/lib/utils";

const CATEGORY_STYLES: Record<string, string> = {
  Feature: "border-primary/20 bg-primary/10 text-primary",
  "Use Case": "border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  Usability: "border-sky-500/20 bg-sky-500/10 text-sky-600 dark:text-sky-400",
};

function formatDate(date: string) {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function BlogPage() {
  const [loginOpen, setLoginOpen] = useState(false);
  const { data: articles = [], isLoading } = useQuery({
    queryKey: ["published-blog-articles"],
    queryFn: () => api.getPublishedBlogArticles(),
  });

  const featured = articles[0];
  const rest = articles.slice(1);

  return (
    <div className="min-h-screen bg-background">
      <MarketingNav onLoginClick={() => setLoginOpen(true)} />
      <main>
        <section className="relative overflow-hidden border-b border-border/60">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.12),transparent_42%)]" />
          <div className="relative mx-auto max-w-6xl px-4 py-16">
            <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              PySetu AI Blog
            </p>
            <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
              Govern every agent, tool, and byte
            </h1>
            <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
              Product deep-dives, real-world use cases, and usability guides for the enterprise AI
              control plane.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {BLOG_CATEGORIES.map((category) => (
                <span
                  key={category}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
                    CATEGORY_STYLES[category]
                  )}
                >
                  <FileText className="h-3 w-3" />
                  {category}
                </span>
              ))}
            </div>
          </div>
        </section>

        {isLoading ? (
          <section className="mx-auto flex max-w-6xl items-center justify-center gap-2 px-4 py-24 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading articles...
          </section>
        ) : articles.length === 0 ? (
          <section className="mx-auto max-w-6xl px-4 py-24 text-center">
            <BookOpen className="mx-auto h-10 w-10 text-muted-foreground/40" />
            <p className="mt-4 font-medium">No articles published yet</p>
            <p className="mt-1 text-sm text-muted-foreground">Check back soon.</p>
          </section>
        ) : (
          <>
            <section className="mx-auto max-w-6xl px-4 py-12">
              <Link
                href={`/blog/${featured.slug}`}
                className="group grid gap-6 overflow-hidden rounded-2xl border border-border/60 bg-card p-6 transition-colors hover:border-primary/30 md:grid-cols-[1.2fr_1fr] md:p-8"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-medium",
                        CATEGORY_STYLES[featured.category] ?? CATEGORY_STYLES.Feature
                      )}
                    >
                      {featured.category}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="h-3 w-3" /> {formatDate(featured.date)}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {featured.read_time}
                    </span>
                  </div>
                  <h2 className="mt-4 text-2xl font-bold tracking-tight group-hover:text-primary md:text-3xl">
                    {featured.title}
                  </h2>
                  <p className="mt-3 text-muted-foreground">{featured.excerpt}</p>
                  <span className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-primary">
                    Read article <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </span>
                </div>
                <div className="flex items-center justify-center overflow-hidden rounded-xl border border-border/50 bg-muted/30">
                  {featured.image_url ? (
                    <img
                      src={featured.image_url}
                      alt={featured.title}
                      className="h-48 w-full object-cover md:h-56"
                    />
                  ) : (
                    <BookOpen className="h-16 w-16 text-primary/40" />
                  )}
                </div>
              </Link>
            </section>

            <section className="mx-auto max-w-6xl px-4 pb-16">
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {rest.map((article: ApiBlogArticle) => (
                  <Link
                    key={article.id}
                    href={`/blog/${article.slug}`}
                    className="group flex flex-col rounded-2xl border border-border/60 bg-card p-5 transition-colors hover:border-primary/30"
                  >
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-medium",
                          CATEGORY_STYLES[article.category] ?? CATEGORY_STYLES.Feature
                        )}
                      >
                        {article.category}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3 w-3" /> {article.read_time}
                      </span>
                    </div>
                <div className="mt-3 flex items-center justify-center overflow-hidden rounded-xl border border-border/50 bg-muted/30">
                  {article.image_url ? (
                    <img
                      src={article.image_url}
                      alt={article.title}
                      className="h-32 w-full object-cover"
                    />
                  ) : (
                    <BookOpen className="h-10 w-10 text-primary/40" />
                  )}
                </div>
                <h3 className="mt-3 text-lg font-semibold leading-snug group-hover:text-primary">
                  {article.title}
                </h3>
                <p className="mt-2 flex-1 text-sm text-muted-foreground">{article.excerpt}</p>
                    <div className="mt-4 flex items-center justify-between border-t border-border/50 pt-3 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="h-3 w-3" /> {formatDate(article.date)}
                      </span>
                      <span className="inline-flex items-center gap-1 font-medium text-primary">
                        Read <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          </>
        )}
      </main>
      <MarketingFooter />
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}
