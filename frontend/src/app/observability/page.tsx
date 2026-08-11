import { redirect } from "next/navigation";

export default function ObservabilityRedirectPage() {
  redirect("/monitoring?tab=traces");
}
