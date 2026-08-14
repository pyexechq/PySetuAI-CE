import { redirect } from "next/navigation";

export default function UagSettingsPage() {
  redirect("/llm-router?tab=gateway");
}
