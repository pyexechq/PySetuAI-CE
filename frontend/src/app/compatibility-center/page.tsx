import { redirect } from "next/navigation";

export default function CompatibilityCenterPage() {
  redirect("/ai-gateway?tab=compatibility");
}
