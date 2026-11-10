"use client";

import { LogOut, Menu } from "lucide-react";
import { useState } from "react";

import { Logo } from "@/components/logo";
import { SidebarNav } from "@/components/layout/sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { useLogout } from "@/hooks/use-auth";
import type { User } from "@/types/auth";

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("");
}

export function Topbar({ user }: { user: User }) {
  const [open, setOpen] = useState(false);
  const logout = useLogout();

  return (
    <header className="bg-background/90 sticky top-0 z-20 flex h-14 items-center gap-3 border-b px-4 backdrop-blur sm:px-6">
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger
          className="hover:bg-muted focus-visible:ring-ring inline-flex size-9 items-center justify-center rounded-lg outline-none focus-visible:ring-2 lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="size-5" />
        </SheetTrigger>
        <SheetContent
          side="left"
          className="bg-sidebar [&_[data-slot=sheet-close]]:text-sidebar-foreground [&_[data-slot=sheet-close]]:hover:bg-sidebar-accent w-72 border-0 p-3 pt-5"
        >
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <div className="px-3 pb-5">
            <Logo
              light
              href={
                user.role === "recruiter" ? "/dashboard" : "/candidate/home"
              }
            />
          </div>
          <SidebarNav role={user.role} onNavigate={() => setOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="flex-1" />

      <DropdownMenu>
        <DropdownMenuTrigger
          className="hover:bg-muted focus-visible:ring-ring flex items-center gap-2 rounded-full p-0.5 pr-2 outline-none focus-visible:ring-2"
          aria-label="Account menu"
        >
          <Avatar className="size-8">
            <AvatarFallback className="bg-secondary text-secondary-foreground text-xs font-medium">
              {initials(user.name)}
            </AvatarFallback>
          </Avatar>
          <span className="hidden text-sm font-medium sm:inline">
            {user.name}
          </span>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuGroup>
            <DropdownMenuLabel>
              <span className="block truncate">{user.email}</span>
              <span className="text-muted-foreground text-xs font-normal capitalize">
                {user.role}
              </span>
            </DropdownMenuLabel>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
          >
            <LogOut />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
