import { PromptTemplateList } from "@/components/settings/prompts/prompt-template-list";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function PromptTemplatesPage() {
  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle>Prompt Templates</CardTitle>
        <CardDescription>
          Manage centrally governed system prompts. Define system prompts, use {"{{var}}"} syntax for variable injection, and set policy enforcement modes (strict or warn) for Gateway ingress.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <PromptTemplateList />
      </CardContent>
    </Card>
  );
}
