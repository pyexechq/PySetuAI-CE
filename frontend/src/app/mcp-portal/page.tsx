import { redirect } from "next/navigation";

export default function McpPortalPage() {
  redirect("/mcp-governance?tab=portal");
}
