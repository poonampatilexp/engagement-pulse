export interface OrganisationRef {
  id: number;
  name: string;
  slug: string;
}

export type UserRole = 'consultant' | 'client_viewer';

export interface UserProfile {
  id: number;
  email: string;
  name: string;
  role: UserRole;
  organisation: OrganisationRef | null;
  organisations: OrganisationRef[] | null;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: UserProfile;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface ApiError {
  message: string;
  status?: number;
  details?: Record<string, any>;
}

