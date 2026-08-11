import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowRight, Workflow, Route, Server, Search } from "lucide-react";
import Link from "next/link";

const modulePreviews = [
  {
    title: "Policy Studio",
    description: "Sensitive Data Protection Policy workflow",
    icon: Workflow,
    href: "/policy-studio",
    badge: "Active",
  },
  {
    title: "LLM Router",
    description: "Cost optimization and security routing enabled",
    icon: Route,
    href: "/llm-router",
    badge: "4 Rules",
  },
  {
    title: "MCP Governance",
    description: "24 MCPs registered, 3 high risk",
    icon: Server,
    href: "/mcp-governance",
    badge: "3 Alerts",
  },
  {
    title: "Audit Explorer",
    description: "High risk request detected — policy actions applied",
    icon: Search,
    href: "/audit-explorer",
    badge: "High Risk",
  },
];

export function ModulePreviews() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {modulePreviews.map((module) => {
        const Icon = module.icon;
        return (
          <Card key={module.title} className="border-border/60 bg-card/50">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="rounded-lg bg-primary/10 p-2">
                    <Icon className="h-4 w-4 text-primary" />
                  </div>
                  <CardTitle className="text-sm">{module.title}</CardTitle>
                </div>
                <Badge variant="secondary" className="text-[10px]">
                  {module.badge}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-xs text-muted-foreground">{module.description}</p>
              <Link href={module.href}>
                <Button variant="ghost" size="sm" className="gap-1 px-0 text-primary">
                  Open module
                  <ArrowRight className="h-3 w-3" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
