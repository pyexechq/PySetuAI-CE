import { Sidebar } from "./sidebar";
import { Header } from "./header";

interface AppShellProps {
  children: React.ReactNode;
  title: string;
  description?: string;
}

export function AppShell({ children, title, description }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex min-h-0 flex-1 flex-col">
        <Header title={title} description={description} />
        <main className="relative min-h-0 flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
