"use client";

import { HelpCircle, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DateRangePicker } from "@/components/layout/date-range-picker";
import { NotificationCenter } from "@/components/layout/notification-center";

interface HeaderProps {
  title: string;
  description?: string;
}

export function Header({ title, description }: HeaderProps) {
  const { theme, setTheme } = useTheme();

  return (
    <header className="relative z-50 flex h-16 shrink-0 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-sm">
      <div>
        <h1 className="text-lg font-semibold text-foreground">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="flex items-center gap-2">
        <DateRangePicker />
        <NotificationCenter />
        <Button variant="ghost" size="icon" aria-label="Help">
          <HelpCircle className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label="Toggle theme"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>
        <Badge variant="secondary" className="hidden sm:inline-flex">
          Live
        </Badge>
      </div>
    </header>
  );
}
