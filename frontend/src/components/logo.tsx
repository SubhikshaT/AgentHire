import Link from "next/link";

import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      aria-hidden="true"
      className={cn("size-8", className)}
    >
      <rect width="32" height="32" rx="9" fill="oklch(0.29 0.08 266)" />
      <path
        d="M9 22.5 15 9.5h2l6 13"
        fill="none"
        stroke="oklch(0.98 0 0)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M11.8 17.5h8.4"
        stroke="oklch(0.72 0.17 295)"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Logo({
  href = "/",
  light = false,
}: {
  href?: string;
  light?: boolean;
}) {
  return (
    <Link
      href={href}
      className="focus-visible:ring-ring flex items-center gap-2.5 rounded-md outline-none focus-visible:ring-2"
    >
      <LogoMark />
      <span
        className={cn(
          "text-lg font-semibold tracking-tight",
          light ? "text-white" : "text-primary",
        )}
      >
        AgentHire
      </span>
    </Link>
  );
}
