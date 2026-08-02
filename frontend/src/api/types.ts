export type Role = "superadmin" | "admin" | "developer" | "viewer";

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_superadmin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface OrgMembershipSummary {
  organization_id: number;
  organization_name: string;
  role: string;
}

export interface DashboardAccessSummary {
  dashboard_id: number;
  dashboard_name: string;
  organization_id: number;
  organization_name: string;
  role: string;
}

export interface Me {
  user: User;
  is_superadmin: boolean;
  primary_role: string;
  permissions: string[];
  admin_organizations: OrgMembershipSummary[];
  dashboard_access: DashboardAccessSummary[];
}

export interface Organization {
  id: number;
  name: string;
  email: string;
  contact_person: string;
  country: string;
  created_at: string;
  created_by_id: number | null;
}

export interface Membership {
  id: number;
  organization_id: number;
  role: string;
  created_at: string;
  user: User;
}

export interface Dashboard {
  id: number;
  organization_id: number;
  name: string;
  description: string | null;
  created_at: string;
  created_by_id: number | null;
}

export interface DashboardAccess {
  id: number;
  dashboard_id: number;
  role: string;
  created_at: string;
  user: User;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface MemberInput {
  email: string;
  full_name?: string;
  password?: string;
}

export interface AccessGrantInput {
  email: string;
  role: "developer" | "viewer";
  full_name?: string;
  password?: string;
}
