import { Metadata } from "next";
import { TenantEdgeMeshPanel } from "@/components/settings/tenant-edge-mesh-panel";

export const metadata: Metadata = {
  title: "Edge Gateway Mesh | PySetu AI Settings",
  description: "Manage tenant private regional edge gateway nodes and VPC data planes.",
};

export default function SettingsEdgeGatewaysPage() {
  return <TenantEdgeMeshPanel />;
}
