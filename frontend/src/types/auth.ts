export type Role = "recruiter" | "candidate";

export type User = {
  id: string;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
};
