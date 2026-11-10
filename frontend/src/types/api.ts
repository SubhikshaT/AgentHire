export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type JobStatus = "draft" | "published" | "closed";
export type Stage =
  | "applied"
  | "resume_reviewed"
  | "shortlisted"
  | "interview_scheduled"
  | "interview_completed"
  | "under_review"
  | "selected"
  | "rejected";

export type EducationRequirement = { level: string; fields: string[] };

export type Job = {
  id: string;
  recruiter_id: string;
  title: string;
  department: string | null;
  description: string;
  required_skills: string[];
  preferred_skills: string[];
  soft_skills: string[];
  minimum_experience: number | null;
  education_requirements: EducationRequirement[];
  certifications: string[];
  responsibilities: string[];
  status: JobStatus;
  is_synthetic: boolean;
  analysis_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  applicant_count: number;
};

export type JobAnalysis = {
  title: string | null;
  department: string | null;
  required_skills: string[];
  preferred_skills: string[];
  soft_skills: string[];
  minimum_experience: number | null;
  education_requirements: EducationRequirement[];
  responsibilities: string[];
  certifications: string[];
};

export type AppSummary = {
  application_id: string;
  job_id: string;
  job_title: string;
  stage: Stage;
  overall_score: number | null;
  match_id: string | null;
  created_at: string;
};

export type CandidateListItem = {
  id: string;
  full_name: string | null;
  email: string | null;
  total_experience_years: number | null;
  top_skills: string[];
  highest_education: string | null;
  is_synthetic: boolean;
  has_account: boolean;
  applications: AppSummary[];
  created_at: string;
};

export type CandidateSkill = {
  id: string;
  skill_key: string;
  name: string;
  category: string | null;
  evidence_text: string | null;
  evidence_section: string | null;
  verification_status: "auto_extracted" | "manually_verified";
  proficiency_level: string | null;
};

export type ResumeBrief = {
  id: string;
  original_filename: string;
  file_type: string;
  parsing_status: "pending" | "processing" | "completed" | "failed";
  parsing_error: string | null;
  uploaded_at: string;
};

export type Education = {
  degree?: string | null;
  level?: string | null;
  field?: string | null;
  institution?: string | null;
  start_year?: number | null;
  end_year?: number | null;
  score?: string | null;
};
export type Experience = {
  title?: string | null;
  company?: string | null;
  start?: string | null;
  end?: string | null;
  months?: number | null;
  description?: string;
  is_internship?: boolean;
};
export type Project = { name: string; description?: string; skills?: string[] };
export type Certification = {
  name: string;
  issuer?: string | null;
  year?: number | null;
};

export type Candidate = {
  id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  professional_summary: string | null;
  total_experience_years: number | null;
  education: Education[];
  work_experience: Experience[];
  projects: Project[];
  certifications: Certification[];
  field_verification: Record<string, string>;
  is_synthetic: boolean;
  has_account: boolean;
  skills: CandidateSkill[];
  resumes: ResumeBrief[];
  applications: AppSummary[];
  created_at: string;
  updated_at: string;
};

export type UploadResult = {
  filename: string;
  ok: boolean;
  resume_id: string | null;
  candidate_id: string | null;
  application_id: string | null;
  error_code: string | null;
  error: string | null;
};

export type ResumeStatus = {
  id: string;
  parsing_status: ResumeBrief["parsing_status"];
  parsing_error: string | null;
  candidate_id: string | null;
  skills_found: number | null;
  warnings: string[];
};

export type Application = {
  id: string;
  candidate_id: string;
  job_id: string;
  job_title: string;
  candidate_name: string | null;
  candidate_email: string | null;
  stage: Stage;
  source: "candidate_applied" | "recruiter_upload";
  created_at: string;
  overall_score: number | null;
  match_id: string | null;
  resume_status: string | null;
  is_synthetic: boolean;
};

export type StageHistory = {
  id: string;
  from_stage: Stage | null;
  to_stage: Stage;
  changed_by_name: string | null;
  changed_at: string;
  note: string | null;
};

export type SkillMatch = {
  skill: string;
  key: string;
  candidate_skill: string;
  credit: number;
  evidence_text?: string | null;
  evidence_section?: string | null;
  verified?: boolean;
  note?: string;
};

export type Explanation = {
  breakdown: {
    component: string;
    raw_value: number;
    weight: number;
    contribution: number;
  }[];
  semantic: {
    raw_cosine: number;
    mapped: number;
    mapping: string;
    note: string;
  };
  required_skills: {
    matched: SkillMatch[];
    related: SkillMatch[];
    missing: string[];
    closest_evidence?: {
      skill: string;
      section: string;
      text: string;
      similarity: number;
    }[];
  };
  preferred_skills: {
    matched: SkillMatch[];
    related: SkillMatch[];
    missing: string[];
  };
  experience: {
    candidate_years: number | null;
    required_years: number | null;
    note: string;
  };
  education: { note: string };
  certifications: { found: string[]; missing: string[] };
  strengths: string[];
  gaps: string[];
  unverified_skills: string[];
  keyword_baseline: number;
  disclaimer: string;
  method_version?: string;
  embedding_model?: string;
};

export type Match = {
  id: string;
  application_id: string;
  candidate_id: string;
  candidate_name: string | null;
  is_synthetic: boolean;
  job_id: string;
  job_title: string;
  stage: Stage;
  overall_score: number;
  keyword_baseline_score: number;
  components: Record<string, number>;
  weights_used: Record<string, number>;
  explanation: Explanation;
  calculated_at: string;
  rank?: number;
};

export type QuestionCategory =
  | "programming"
  | "dsa"
  | "dbms"
  | "os"
  | "networks"
  | "software_engineering"
  | "system_design"
  | "project"
  | "behavioral";
export type Difficulty = "beginner" | "intermediate" | "advanced";

export type AnswerFeedback = {
  strengths?: string[];
  weaknesses?: string[];
  missing_concepts?: string[];
  explanation?: string;
  suggested_improvement?: string;
  evidence_quotes?: string[];
  method?: string;
  error?: string;
  submitted_on_finish?: boolean;
};

export type InterviewQuestion = {
  id: string;
  sequence_number: number;
  question: string;
  category: QuestionCategory;
  category_label: string;
  difficulty: Difficulty;
  time_limit_seconds: number;
  source: "llm" | "question_bank" | "recruiter";
  grounding: string | null;
  is_follow_up: boolean;
  expected_concepts?: string[];
  evaluation_rubric?: string[];
  answer?: {
    text: string | null;
    submitted_at: string | null;
    evaluation_status: "not_submitted" | "pending_llm" | "evaluated" | "failed";
    verdict: string | null;
    weighted_score: number | null;
    scores: Record<string, number> | null;
    feedback: AnswerFeedback;
    concept_coverage: { covered: string[]; missing: string[]; note: string };
    evaluated_at: string | null;
  };
};

export type Interview = {
  id: string;
  application_id: string;
  job_id: string;
  job_title: string;
  candidate_id: string;
  candidate_name: string | null;
  interview_type: "assigned" | "practice";
  status: "draft" | "ready" | "in_progress" | "completed";
  difficulty: Difficulty;
  categories: QuestionCategory[];
  question_count: number;
  started_at: string | null;
  completed_at: string | null;
  total_score: number | null;
  created_at: string;
  questions: InterviewQuestion[];
  questions_hidden_until_start: boolean;
  can_manage: boolean;
  is_candidate: boolean;
  rubric_version: string;
};

export type InterviewListItem = {
  id: string;
  application_id: string;
  job_title: string;
  candidate_name: string | null;
  interview_type: "assigned" | "practice";
  status: Interview["status"];
  difficulty: Difficulty;
  question_count: number;
  answered: number;
  total_score: number | null;
  pending_evaluation: number;
  created_at: string;
  completed_at: string | null;
};

export type CurrentQuestion =
  | { done: true; answered: number; total: number }
  | {
      done: false;
      answered: number;
      total: number;
      question: {
        id: string;
        number: number;
        text: string;
        category: string;
        category_label: string;
        difficulty: Difficulty;
        time_limit_seconds: number;
        is_follow_up: boolean;
      };
      draft_text: string;
      seconds_remaining: number;
    };

export type LlmStatus = {
  provider: string;
  model: string | null;
  configured: boolean;
  available: boolean;
  sends_data_externally: boolean;
  message: string;
  vector_backend: string;
  embedding_model: string;
};

export type LearningItem = {
  key: string;
  title: string;
  url: string;
  objective: string;
  difficulty: string;
  skill: string;
  priority: "required" | "related" | "preferred";
  note: string | null;
  completed?: boolean;
};

export type ReportListItem = {
  id: string;
  application_id: string;
  job_id: string;
  job_title: string;
  candidate_name: string | null;
  is_synthetic: boolean;
  overall_score: number | null;
  interview_score: number | null;
  has_interview: boolean;
  generated_at: string;
  methodology_version: string;
};

export type Report = {
  id: string;
  application_id: string;
  interview_id: string | null;
  methodology_version: string;
  generated_at: string;
  report_data: {
    candidate: {
      id: string;
      name: string | null;
      email: string | null;
      is_synthetic: boolean;
      total_experience_years: number | null;
      education: Education[];
      certifications: Certification[];
      skills: { name: string; section: string | null; status: string }[];
      work_experience: Experience[];
      projects: Project[];
    };
    job: {
      id: string;
      title: string;
      required_skills: string[];
      preferred_skills: string[];
    };
    stage: Stage;
    match: null | {
      overall_score: number;
      keyword_baseline_score: number;
      weights_used: Record<string, number>;
      explanation: Explanation;
      calculated_at: string;
    };
    interview: null | {
      id: string;
      status: string;
      difficulty: string;
      total_score: number | null;
      completed_at: string | null;
      questions: InterviewQuestion[];
      summary: {
        answered: number;
        evaluated: number;
        pending: number;
        verdicts: Record<string, number>;
      };
      rubric_version: string;
    };
    learning_recommendations: LearningItem[];
    limitations: string[];
    versions: Record<string, string>;
    generated_by: string;
  };
  notes: {
    id: string;
    text: string;
    author: string | null;
    created_at: string;
    label: string;
  }[];
};
