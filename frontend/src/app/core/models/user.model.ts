export type UserRole = 'admin' | 'customer' | 'guest';

export interface AuthUser {
  id: string;
  emailAddress: string;
  fullName: string;
  role: UserRole;
}
