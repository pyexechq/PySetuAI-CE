"use client";

import Link from "next/link";
import { ArrowLeft, ArrowUpRight, Clock, Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { HELP_GUIDE_ICONS } from "@/config/help-resources";
import type { HelpGuideArticle } from "@/config/help-resources";

export function HelpGuideArticleView({ article }: { article: HelpGuideArticle }) {
  const Icon = HELP_GUIDE_ICONS[article.icon];

  return (
    <div className="space-y-6">
      <Link
        href="/help?tab=guides"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to product guides
      </Link>

      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="rounded-lg bg-primary/10 p-2.5">
                <Icon className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-xl">{article.label}</CardTitle>
                <CardDescription className="mt-1 max-w-2xl text-sm">{article.summary}</CardDescription>
                <p className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3.5 w-3.5" />
                  {article.readMinutes} min read
                </p>
              </div>
            </div>
            <Button asChild variant="outline" size="sm" className="gap-1.5">
              <Link href={article.featureHref}>
                Open {article.label}
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        </CardHeader>
      </Card>

      <div className="space-y-6">
        {article.sections.map((section) => (
          <section key={section.title} className="space-y-3">
            <h2 className="text-base font-semibold text-foreground">{section.title}</h2>
            <div className="space-y-3 text-sm leading-relaxed text-muted-foreground">
              {section.paragraphs.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </div>
          </section>
        ))}
      </div>

      {article.tips.length > 0 && (
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Lightbulb className="h-4 w-4 text-primary" />
              Tips
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
              {article.tips.map((tip) => (
                <li key={tip}>{tip}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
