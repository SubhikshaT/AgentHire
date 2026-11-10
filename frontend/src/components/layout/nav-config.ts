import {
  BarChart3,
  Briefcase,
  ClipboardList,
  FileText,
  GraduationCap,
  LayoutDashboard,
  MessageSquareText,
  ScrollText,
  Search,
  Settings,
  Upload,
  UserRound,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { Role } from "@/types/auth";

export type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Build phase in which this page is delivered. Items from later phases render disabled. */
  phase: number;
};

// Update CURRENT_PHASE as each phase is completed and verified.
export const CURRENT_PHASE = 7;

export const NAV: Record<Role, NavItem[]> = {
  recruiter: [
    { label: "Overview", href: "/dashboard", icon: LayoutDashboard, phase: 1 },
    { label: "Jobs", href: "/jobs", icon: Briefcase, phase: 2 },
    { label: "Candidates", href: "/candidates", icon: Users, phase: 2 },
    { label: "Resume Screening", href: "/resumes", icon: Upload, phase: 2 },
    {
      label: "Interviews",
      href: "/interviews",
      icon: MessageSquareText,
      phase: 4,
    },
    { label: "Reports", href: "/reports", icon: ScrollText, phase: 5 },
    { label: "Skill Analytics", href: "/analytics", icon: BarChart3, phase: 6 },
    { label: "Settings", href: "/settings", icon: Settings, phase: 5 },
  ],
  candidate: [
    { label: "Home", href: "/candidate/home", icon: LayoutDashboard, phase: 1 },
    {
      label: "My Profile",
      href: "/candidate/profile",
      icon: UserRound,
      phase: 2,
    },
    { label: "Browse Jobs", href: "/candidate/jobs", icon: Search, phase: 2 },
    {
      label: "My Applications",
      href: "/candidate/applications",
      icon: ClipboardList,
      phase: 2,
    },
    {
      label: "Interviews",
      href: "/candidate/interviews",
      icon: MessageSquareText,
      phase: 4,
    },
    {
      label: "My Feedback",
      href: "/candidate/feedback",
      icon: FileText,
      phase: 5,
    },
    {
      label: "Learning",
      href: "/candidate/learning",
      icon: GraduationCap,
      phase: 6,
    },
    {
      label: "Settings",
      href: "/candidate/settings",
      icon: Settings,
      phase: 5,
    },
  ],
};

/** Which role may open a given path. */
export function roleForPath(pathname: string): Role {
  return pathname === "/candidate" || pathname.startsWith("/candidate/")
    ? "candidate"
    : "recruiter";
}
