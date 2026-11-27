export type Role =
  | "admin"
  | "order_manager"
  | "floor_supervisor"
  | "qa_inspector"
  | "auditor";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  department: string;
  role: Role;
  role_display_name: string;
  is_active: boolean;
  permissions: string[];
  created_at: string;
  last_login_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserProfile;
}

export interface RolePermissionSummary {
  role: Role;
  display_name: string;
  department: string;
  description: string;
  permissions: string[];
}

export interface RoleMatrixResponse {
  roles: RolePermissionSummary[];
  all_permissions: string[];
}
