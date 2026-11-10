import { Suspense } from "react";

import { AppShell } from "@/components/layout/app-shell";

function ShellFallback() {
  return (
    <div className="flex min-h-screen" aria-busy="true" aria-label="Loading">
      <div className="bg-sidebar hidden w-64 lg:block" />
      <div className="flex-1 p-6" />
    </div>
  );
}

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <Suspense fallback={<ShellFallback />}>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
