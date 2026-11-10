import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
      <p className="text-accent-foreground text-sm font-medium">404</p>
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="text-muted-foreground text-sm">
        The page you are looking for does not exist.
      </p>
      <Link
        href="/"
        className={buttonVariants({ variant: "outline", className: "mt-2" })}
      >
        Back to home
      </Link>
    </div>
  );
}
