import { Role, UserProfile } from "./auth";

export interface DashboardStat {
  key: string;
  label: string;
  value: string;
  caption: string;
}

export interface DashboardModule {
  key: string;
  title: string;
  description: string;
  route: string;
  required_permission: string;
  enabled: boolean;
  status: string;
}

export interface AuditLogItem {
  id: string;
  actor_id: string | null;
  actor_email: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  status: string;
  details: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface RoleDashboardResponse {
  role: Role;
  role_display_name: string;
  department: string;
  database_connected: boolean;
  stats: DashboardStat[];
  modules: DashboardModule[];
  role_distribution: Record<string, number>;
  recent_activity: AuditLogItem[];
  permissions: string[];
}

export interface UserListResponse {
  items: UserProfile[];
  total: number;
}

export interface AuditLogListResponse {
  items: AuditLogItem[];
  total: number;
}

export interface WorkspaceCheckResponse {
  workspace: string;
  role: Role;
  can_manage: boolean;
  phase: string;
}
