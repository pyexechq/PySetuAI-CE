import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Construction } from "lucide-react";

interface ModulePlaceholderProps {
  title: string;
  description: string;
  phase: string;
}

export function ModulePlaceholder({ title, description, phase }: ModulePlaceholderProps) {
  return (
    <AppShell title={title} description={description}>
      <Card className="max-w-2xl border-border/60">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-3">
              <Construction className="h-6 w-6 text-primary" />
            </div>
            <div>
              <CardTitle>{title}</CardTitle>
              <CardDescription className="mt-1">{description}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Badge variant="secondary">{phase}</Badge>
          <p className="mt-4 text-sm text-muted-foreground">
            This module is scaffolded in the navigation and routing layer. Implementation is
            tracked in the product roadmap and current sprint documentation.
          </p>
        </CardContent>
      </Card>
    </AppShell>
  );
}
