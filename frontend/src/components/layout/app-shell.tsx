"use client";

import { AlertCircle } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { roleForPath } from "@/components/layout/nav-config";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { homePathFor, useMe } from "@/hooks/use-auth";
import { errorMessage } from "@/lib/api";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { data: user, isPending, isError, error, refetch } = useMe();
  const pathname = usePathname();
  const router = useRouter();
  const wrongRole = !!user && roleForPath(pathname) !== user.role;

  useEffect(() => {
    if (isPending || isError) return;
    if (user === null)
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (wrongRole) router.replace(homePathFor(user.role));
  }, [user, isPending, isError, wrongRole, pathname, router]);

  if (isError) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-sm text-center">
          <AlertCircle className="text-destructive mx-auto size-8" />
          <p className="mt-3 font-medium">Could not load your account</p>
          <p className="text-muted-foreground mt-1 text-sm">
            {errorMessage(error)}
          </p>
          <Button className="mt-4" onClick={() => refetch()}>
            Try again
          </Button>
        </div>
      </div>
    );
  }

  if (isPending || !user || wrongRole) {
    return (
      <div className="flex min-h-screen" aria-busy="true" aria-label="Loading">
        <div className="bg-sidebar hidden w-64 lg:block" />
        <div className="flex-1 space-y-4 p-6">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar role={user.role} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar user={user} />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
