"use client";

import { use, useState } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Calendar, CheckCircle2, Clock, FileText, Lightbulb, Loader2, User } from "lucide-react";
import { api, type ApiBlogArticle } from "@/lib/api";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { LoginModal } from "@/components/auth/login-modal";
import { BlogArticleHero } from "@/components/blog/blog-article-hero";
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

export default function BlogArticlePage({ params }: { params: Promise<{ slug: string }> }) {
  const [loginOpen, setLoginOpen] = useState(false);
  const { slug } = use(params);

  const { data: article, isLoading, isError } = useQuery({
    queryKey: ["published-blog-article", slug],
    queryFn: () => api.getPublishedBlogArticle(slug),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <MarketingNav onLoginClick={() => setLoginOpen(true)} />
        <main className="mx-auto flex max-w-3xl items-center justify-center gap-2 px-4 py-24 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading article...
        </main>
        <MarketingFooter />
        <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
      </div>
    );
  }

  if (isError || !article) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-background">
      <MarketingNav onLoginClick={() => setLoginOpen(true)} />
      <main>
        <article className="mx-auto max-w-3xl px-4 py-12">
          <Link
            href="/blog"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" /> All articles
          </Link>

          <div className="mt-6 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-medium",
                CATEGORY_STYLES[article.category] ?? CATEGORY_STYLES.Feature
              )}
            >
              <FileText className="h-3 w-3" /> {article.category}
            </span>
            <span className="inline-flex items-center gap-1">
              <Calendar className="h-3 w-3" /> {formatDate(article.date)}
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" /> {article.read_time}
            </span>
            <span className="inline-flex items-center gap-1">
              <User className="h-3 w-3" /> {article.author}
            </span>
          </div>

          <h1 className="mt-4 text-3xl font-bold tracking-tight md:text-4xl">{article.title}</h1>
          <p className="mt-4 text-lg text-muted-foreground">{article.excerpt}</p>

          <div className="mt-6 flex flex-wrap gap-2">
            {(article.tags || []).map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-border/60 bg-muted/40 px-2.5 py-0.5 text-xs text-muted-foreground"
              >
                #{tag}
              </span>
            ))}
          </div>

          <BlogArticleHero feature={article.feature} image_url={article.image_url} />

          <div className="mt-8 rounded-2xl border border-primary/20 bg-primary/5 p-5">
            <p className="flex items-center gap-2 text-sm font-semibold text-primary">
              <Lightbulb className="h-4 w-4" /> Key takeaways
            </p>
            <ul className="mt-3 space-y-2">
              {(article.content || []).slice(0, 3).map((section) => (
                <li key={section.heading} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary/70" />
                  <span>
                    <span className="font-medium text-foreground">{section.heading}:</span>{" "}
                    {section.body[0]}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-10 space-y-10 border-t border-border/60 pt-10">
            {(article.content || []).map((section) => (
              <section key={section.heading}>
                <h2 className="text-2xl font-bold tracking-tight">{section.heading}</h2>
                {section.body.map((paragraph, i) => (
                  <p key={i} className="mt-4 leading-relaxed text-muted-foreground">
                    {paragraph}
                  </p>
                ))}
              </section>
            ))}
          </div>
        </article>

        <section className="border-t border-border/60 bg-muted/20 py-12">
          <div className="mx-auto max-w-3xl px-4">
            <div className="relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/10 via-background to-background p-8 text-center">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.12),transparent_50%)]" />
              <div className="relative">
                <h3 className="text-2xl font-bold tracking-tight">See it in action</h3>
                <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
                  Explore {article.feature} in the PySetu AI control plane and see how it governs
                  every agent, tool, and byte.
                </p>
                <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                  <button
                    type="button"
                    onClick={() => setLoginOpen(true)}
                    className="rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                  >
                    Try the platform
                  </button>
                  <Link
                    href="/blog"
                    className="rounded-md border border-border bg-background px-5 py-2.5 text-sm font-medium transition-colors hover:bg-muted"
                  >
                    Browse more articles
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
      <MarketingFooter />
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}
