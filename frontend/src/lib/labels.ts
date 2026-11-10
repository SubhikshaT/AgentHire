import type { QuestionCategory, Stage } from "@/types/api";

export const STAGES: { value: Stage; label: string }[] = [
  { value: "applied", label: "Applied" },
  { value: "resume_reviewed", label: "Resume reviewed" },
  { value: "shortlisted", label: "Shortlisted" },
  { value: "interview_scheduled", label: "Interview scheduled" },
  { value: "interview_completed", label: "Interview completed" },
  { value: "under_review", label: "Under review" },
  { value: "selected", label: "Selected" },
  { value: "rejected", label: "Rejected" },
];

export const stageLabel = (s: string) =>
  STAGES.find((x) => x.value === s)?.label ?? s;

export const stageTone = (s: string) =>
  s === "selected"
    ? "bg-success/15 text-success"
    : s === "rejected"
      ? "bg-destructive/10 text-destructive"
      : s === "applied"
        ? "bg-muted text-muted-foreground"
        : "bg-secondary text-secondary-foreground";

export const CATEGORIES: { value: QuestionCategory; label: string }[] = [
  { value: "programming", label: "Programming" },
  { value: "dsa", label: "Data Structures & Algorithms" },
  { value: "dbms", label: "Database Management" },
  { value: "os", label: "Operating Systems" },
  { value: "networks", label: "Computer Networks" },
  { value: "software_engineering", label: "Software Engineering" },
  { value: "system_design", label: "System Design" },
  { value: "project", label: "Project-Based" },
  { value: "behavioral", label: "Behavioral" },
];

export const COMPONENT_LABELS: Record<string, string> = {
  semantic: "Semantic similarity",
  required_skills: "Required skills",
  preferred_skills: "Preferred skills",
  experience: "Experience",
  education: "Education",
  certifications: "Certifications",
};

export const RUBRIC_LABELS: Record<string, string> = {
  technical_correctness: "Technical correctness",
  conceptual_understanding: "Conceptual understanding",
  problem_solving: "Problem-solving approach",
  clarity: "Clarity",
  relevance: "Relevance",
};

export const VERDICT_LABELS: Record<string, string> = {
  correct: "Correct",
  partially_correct: "Partially correct",
  incorrect: "Incorrect",
  insufficient: "Insufficient information",
};

export const EDU_LEVELS = [
  { value: "secondary", label: "Secondary (10th)" },
  { value: "higher_secondary", label: "Higher secondary (12th)" },
  { value: "diploma", label: "Diploma" },
  { value: "bachelors", label: "Bachelor's" },
  { value: "masters", label: "Master's" },
  { value: "phd", label: "PhD" },
];

export function scoreTone(score: number | null | undefined) {
  if (score === null || score === undefined) return "text-muted-foreground";
  if (score >= 70) return "text-success";
  if (score >= 45) return "text-amber-600";
  return "text-destructive";
}

export function fmtDate(iso: string | null | undefined, withTime = false) {
  if (!iso) return "—";
  const d = new Date(iso);
  return withTime
    ? d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
    : d.toLocaleDateString(undefined, { dateStyle: "medium" });
}

export function fmtScore(n: number | null | undefined, digits = 1) {
  return n === null || n === undefined ? "—" : n.toFixed(digits);
}

export const ACTION_LABELS: Record<string, string> = {
  "user.registered": "Account created",
  "user.login": "Logged in",
  "job.created": "Created a job",
  "job.updated": "Edited a job",
  "job.deleted": "Deleted a job",
  "job.published": "Published a job",
  "job.draft": "Unpublished a job",
  "job.closed": "Closed a job",
  "job.analyzed": "Analyzed a job description",
  "resume.uploaded": "Uploaded a resume",
  "resume.duplicate_linked": "Linked an existing candidate",
  "resume.reprocess": "Re-parsed a resume",
  "candidate.corrected": "Corrected a profile",
  "candidate.skills_edited": "Edited candidate skills",
  "candidate.deleted": "Deleted a candidate",
  "application.stage_changed": "Moved a candidate",
  "application.removed": "Removed an applicant",
  "matching.run": "Ran matching",
  "interview.created": "Created an interview",
  "interview.questions_generated": "Generated questions",
  "interview.questions_edited": "Edited questions",
  "interview.evaluated": "Evaluated an interview",
  "report.generated": "Generated a report",
  "report.note_added": "Added a report note",
  "report.pdf_built": "Downloaded a report PDF",
  "settings.matching_weights": "Changed matching weights",
  "settings.rubric_weights": "Changed rubric weights",
};
