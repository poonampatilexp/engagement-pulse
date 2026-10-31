import { LoginCredentials, LoginResponse, UserProfile, ApiError } from '@/types/auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

const STATUS_MESSAGES: Record<number, string> = {
  401: 'Invalid email or password. Please verify your credentials.',
  403: 'Access denied. You do not have permission for this resource.',
  404: 'Resource not found.',
};

export class ApiClientError extends Error {
  status: number;
  details?: Record<string, any>;

  constructor(message: string, status = 500, details?: Record<string, any>) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.details = details;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    const isJson = response.headers.get('content-type')?.includes('application/json');
    const data = isJson ? await response.json() : null;

    if (!response.ok) {
      const errorMessage =
        data?.detail ??
        data?.message ??
        data?.non_field_errors?.[0] ??
        data?.email?.[0] ??
        data?.password?.[0] ??
        STATUS_MESSAGES[response.status] ??
        'An unexpected error occurred. Please try again.';

      throw new ApiClientError(errorMessage, response.status, data);
    }

    return data as T;
  } catch (error: any) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    // Network or fetch failure
    throw new ApiClientError(
      'Unable to connect to the authentication server. Please ensure the backend is running.',
      0
    );
  }
}

export const apiClient = {
  auth: {
    login(credentials: LoginCredentials): Promise<LoginResponse> {
      return request<LoginResponse>('/api/auth/login/', {
        method: 'POST',
        body: JSON.stringify(credentials),
      });
    },

    getMe(accessToken: string): Promise<UserProfile> {
      return request<UserProfile>('/api/auth/me/', {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
    },
  },
};

