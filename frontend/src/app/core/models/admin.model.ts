import { UserRole } from './user.model';

export type AccountStatus = 'active' | 'suspended';

export interface AdminUserSummary {
  id: string;
  emailAddress: string;
  fullName: string;
  role: UserRole;
  status: AccountStatus;
  createdAt: string;
  lastLoginAt: string | null;
}

export interface AccountNote {
  id: string;
  authorName: string;
  body: string;
  createdAt: string;
}
