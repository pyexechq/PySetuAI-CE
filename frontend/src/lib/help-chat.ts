export interface HelpHighlight {
  helpId: string;
  label: string;
  reason: string;
}

export interface HelpChatLink {
  href: string;
  label: string;
}

export interface HelpChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  highlights?: HelpHighlight[];
  links?: HelpChatLink[];
  aiEnhanced?: boolean;
}

export function collectVisibleHelpIds(): string[] {
  if (typeof document === "undefined") return [];
  return Array.from(document.querySelectorAll("[data-help-id]"))
    .map((el) => el.getAttribute("data-help-id"))
    .filter((id): id is string => Boolean(id));
}

export function highlightHelpTarget(helpId: string): boolean {
  const el = document.querySelector(`[data-help-id="${helpId}"]`);
  if (!el || !(el instanceof HTMLElement)) return false;

  el.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
  el.classList.add("help-spotlight");
  window.setTimeout(() => el.classList.remove("help-spotlight"), 3200);
  return true;
}

export function clearHelpSpotlights() {
  document.querySelectorAll(".help-spotlight").forEach((el) => el.classList.remove("help-spotlight"));
}
