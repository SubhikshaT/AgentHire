"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Logo } from "@/components/logo";
import { CURRENT_PHASE, NAV } from "@/components/layout/nav-config";
import { cn } from "@/lib/utils";
import type { Role } from "@/types/auth";

export function SidebarNav({
  role,
  onNavigate,
}: {
  role: Role;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5">
      {NAV[role].map(({ label, href, icon: Icon, phase }) => {
        const ready = phase <= CURRENT_PHASE;
        const active = pathname === href || pathname.startsWith(`${href}/`);
        if (!ready) {
          return (
            <span
              key={href}
              aria-disabled="true"
              title={`Arrives in build phase ${phase}`}
              className="text-sidebar-foreground/40 flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2 text-sm"
            >
              <Icon className="size-4 shrink-0" />
              <span className="flex-1">{label}</span>
              <span className="border-sidebar-border rounded border px-1.5 text-[10px] tabular-nums">
                P{phase}
              </span>
            </span>
          );
        }
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "focus-visible:ring-sidebar-ring flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors outline-none focus-visible:ring-2",
              active
                ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
            )}
          >
            <Icon
              className={cn(
                "size-4 shrink-0",
                active && "text-sidebar-primary",
              )}
            />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar({ role }: { role: Role }) {
  return (
    <aside className="bg-sidebar sticky top-0 hidden h-screen w-64 shrink-0 flex-col px-3 py-5 lg:flex">
      <div className="px-3 pb-6">
        <Logo
          light
          href={role === "recruiter" ? "/dashboard" : "/candidate/home"}
        />
      </div>
      <SidebarNav role={role} />
      <p className="text-sidebar-foreground/45 mt-auto px-3 text-[11px] leading-relaxed">
        AI scores support your judgement. They are not hiring decisions.
      </p>
    </aside>
  );
}
