import {
  BrainCircuit,
  FileSearch,
  GitCompareArrows,
  MessageSquareText,
  ScrollText,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";

import { Logo } from "@/components/logo";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: FileSearch,
    title: "Resume parsing",
    text: "PDF and DOCX resumes become structured profiles. Every skill keeps the line it came from.",
  },
  {
    icon: GitCompareArrows,
    title: "Hybrid matching",
    text: "Semantic similarity plus skill, experience, education and certification coverage. Weights are yours to set.",
  },
  {
    icon: BrainCircuit,
    title: "Explainable scores",
    text: "Each score shows matched skills, related-but-different skills, gaps, and how much every part contributed.",
  },
  {
    icon: MessageSquareText,
    title: "Mock interviews",
    text: "Questions grounded in the job and the resume. Autosave, resume later, never auto-submitted.",
  },
  {
    icon: ScrollText,
    title: "Rubric evaluation",
    text: "Answers are scored on fixed dimensions with quoted evidence, then summarized in a downloadable report.",
  },
  {
    icon: ShieldCheck,
    title: "Human decisions",
    text: "No automatic rejections. Personal details are kept out of scoring, and every AI output is audited.",
  },
];

const steps = [
  [
    "Post a job",
    "Paste a description. AgentHire pulls out required and preferred skills for you to review.",
  ],
  [
    "Upload resumes",
    "Drop in many files at once. Parsing runs in the background with clear status.",
  ],
  [
    "Review matches",
    "See ranked candidates with the evidence behind every number.",
  ],
  [
    "Interview & decide",
    "Run a text interview, read the rubric-based evaluation, add your notes, decide.",
  ],
];

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="bg-background/85 sticky top-0 z-30 border-b backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Logo />
          <nav className="flex items-center gap-2" aria-label="Account">
            <Link
              href="/login"
              className={buttonVariants({ variant: "ghost", size: "lg" })}
            >
              Log in
            </Link>
            <Link href="/register" className={buttonVariants({ size: "lg" })}>
              Create account
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <section className="bg-primary text-primary-foreground relative overflow-hidden">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 [background-image:linear-gradient(to_right,white_1px,transparent_1px),linear-gradient(to_bottom,white_1px,transparent_1px)] [background-size:44px_44px] opacity-[0.07]"
          />
          <div className="relative mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 md:grid-cols-[1.15fr_1fr] md:py-28">
            <div>
              <p className="mb-4 inline-flex rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium tracking-wide text-violet-200">
                Recruitment decision support
              </p>
              <h1 className="text-4xl leading-[1.08] font-semibold tracking-tight text-balance sm:text-5xl">
                Screen faster. Explain every score.
              </h1>
              <p className="text-primary-foreground/75 mt-5 max-w-xl text-lg text-pretty">
                AgentHire reads resumes, matches them to your jobs, and runs
                first-round text interviews — then shows you exactly why each
                candidate scored the way they did. You make the call.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href="/register?role=recruiter"
                  className={cn(
                    buttonVariants({ size: "lg" }),
                    "text-primary h-11 bg-white px-5 hover:bg-white/90",
                  )}
                >
                  I&apos;m hiring
                </Link>
                <Link
                  href="/register?role=candidate"
                  className={cn(
                    buttonVariants({ variant: "outline", size: "lg" }),
                    "h-11 border-white/25 bg-transparent px-5 text-white hover:bg-white/10 hover:text-white",
                  )}
                >
                  I&apos;m looking for a job
                </Link>
              </div>
            </div>

            <div aria-hidden="true" className="hidden md:block">
              <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-5 shadow-2xl">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white/60">Backend Engineer</p>
                    <p className="font-medium">Example score breakdown</p>
                  </div>
                  <span className="rounded-full bg-violet-400/20 px-2.5 py-1 text-xs text-violet-100">
                    sample
                  </span>
                </div>
                <div className="mt-5 space-y-3 text-sm">
                  {[
                    ["Semantic similarity", 35, 0.72],
                    ["Required skills", 30, 0.75],
                    ["Preferred skills", 10, 0.5],
                    ["Experience", 15, 1],
                    ["Education", 5, 1],
                    ["Certifications", 5, 1],
                  ].map(([label, weight, value]) => (
                    <div key={label as string}>
                      <div className="mb-1 flex justify-between text-white/70">
                        <span>{label}</span>
                        <span className="tabular-nums">weight {weight}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-white/10">
                        <div
                          className="h-1.5 rounded-full bg-violet-300"
                          style={{ width: `${(value as number) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <p className="mt-5 text-xs text-white/50">
                  Illustration of the layout only — real breakdowns are computed
                  from each resume.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section
          className="mx-auto max-w-6xl px-4 py-20 sm:px-6"
          aria-labelledby="features"
        >
          <h2
            id="features"
            className="text-2xl font-semibold tracking-tight sm:text-3xl"
          >
            What it does
          </h2>
          <div className="mt-10 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
            {features.map(({ icon: Icon, title, text }) => (
              <div key={title}>
                <div className="bg-secondary text-secondary-foreground flex size-10 items-center justify-center rounded-lg">
                  <Icon className="size-5" />
                </div>
                <h3 className="mt-4 font-medium">{title}</h3>
                <p className="text-muted-foreground mt-1.5 text-sm leading-relaxed">
                  {text}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-muted/60 border-y" aria-labelledby="how">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
            <h2
              id="how"
              className="text-2xl font-semibold tracking-tight sm:text-3xl"
            >
              How it works
            </h2>
            <ol className="mt-10 grid gap-6 md:grid-cols-4">
              {steps.map(([title, text], i) => (
                <li key={title} className="bg-card rounded-xl border p-5">
                  <span className="text-accent-foreground text-sm font-semibold tabular-nums">
                    0{i + 1}
                  </span>
                  <h3 className="mt-2 font-medium">{title}</h3>
                  <p className="text-muted-foreground mt-1.5 text-sm leading-relaxed">
                    {text}
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section
          className="mx-auto max-w-6xl px-4 py-20 sm:px-6"
          aria-labelledby="principles"
        >
          <h2
            id="principles"
            className="text-2xl font-semibold tracking-tight sm:text-3xl"
          >
            Built to support people, not replace them
          </h2>
          <ul className="text-muted-foreground mt-6 grid gap-3 text-sm sm:grid-cols-2">
            <li>• A match score is not a probability of being hired.</li>
            <li>
              • Gender, age, photos and other protected traits are never used.
            </li>
            <li>• The system never moves anyone to “Rejected” on its own.</li>
            <li>• Runs fully on your machine — no paid AI service required.</li>
          </ul>
        </section>
      </main>

      <footer className="border-t">
        <div className="text-muted-foreground mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-6 text-sm sm:px-6">
          <span>AgentHire — final-year project</span>
          <span>AI scores are decision support only.</span>
        </div>
      </footer>
    </div>
  );
}
