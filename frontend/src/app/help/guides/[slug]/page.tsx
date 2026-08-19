import { notFound } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { HelpGuideArticleView } from "@/components/help/help-guide-article-view";
import { getHelpGuideArticle, listHelpGuideSlugs } from "@/config/help-resources";

interface HelpGuidePageProps {
  params: Promise<{ slug: string }>;
}

export function generateStaticParams() {
  return listHelpGuideSlugs().map((slug) => ({ slug }));
}

export default async function HelpGuidePage({ params }: HelpGuidePageProps) {
  const { slug } = await params;
  const article = getHelpGuideArticle(slug);
  if (!article) notFound();

  return (
    <AppShell title={article.label} description={`Help guide · ${article.readMinutes} min read`}>
      <HelpGuideArticleView article={article} />
    </AppShell>
  );
}
