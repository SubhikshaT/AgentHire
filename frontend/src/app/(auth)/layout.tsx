import { Logo } from "@/components/logo";

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_1.1fr]">
      <aside className="bg-primary text-primary-foreground relative hidden flex-col justify-between overflow-hidden p-10 lg:flex">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 [background-image:linear-gradient(to_right,white_1px,transparent_1px),linear-gradient(to_bottom,white_1px,transparent_1px)] [background-size:44px_44px] opacity-[0.07]"
        />
        <div className="relative">
          <Logo light />
        </div>
        <div className="relative max-w-md">
          <p className="text-2xl leading-snug font-medium text-balance">
            Every score comes with the evidence behind it.
          </p>
          <p className="text-primary-foreground/65 mt-3 text-sm">
            Matched skills, gaps and rubric scores are shown side by side, so
            the final decision stays with you.
          </p>
        </div>
        <p className="text-primary-foreground/45 relative text-xs">
          AI output is decision support, not a hiring decision.
        </p>
      </aside>
      <main className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Logo />
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
