import { LoginCredentials, LoginResponse, UserProfile } from '@/types/auth';

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

// In-memory access token storage (never touches localStorage or cookies)
let inMemoryAccessToken: string | null = null;
let onTokenRefreshedCallback: ((token: string) => void) | null = null;
let onAuthFailureCallback: (() => void) | null = null;

// Shared in-flight refresh promise for concurrent request deduplication
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

export function setOnTokenRefreshed(callback: ((token: string) => void) | null): void {
  onTokenRefreshedCallback = callback;
}

export function setOnAuthFailure(callback: (() => void) | null): void {
  onAuthFailureCallback = callback;
}

/**
 * Executes a token refresh with deduplication.
 * Multiple concurrent callers receive the same pending promise to prevent duplicate refresh calls.
 */
export async function refreshAccessToken(explicitToken?: string): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const body = explicitToken ? JSON.stringify({ refresh: explicitToken }) : undefined;
      const response = await fetch(`${API_BASE}/api/auth/refresh/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body,
      });

      if (!response.ok) {
        inMemoryAccessToken = null;
        onAuthFailureCallback?.();
        return null;
      }

      const data = await response.json();
      const newAccessToken = data.access;
      inMemoryAccessToken = newAccessToken;
      onTokenRefreshedCallback?.(newAccessToken);
      return newAccessToken;
    } catch (err) {
      inMemoryAccessToken = null;
      onAuthFailureCallback?.();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

interface ExtendedRequestInit extends RequestInit {
  _retry?: boolean;
}

export async function request<T>(endpoint: string, options: ExtendedRequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  // Attach in-memory JWT bearer token if available and not already set
  if (inMemoryAccessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${inMemoryAccessToken}`);
  }

  const fetchOptions: ExtendedRequestInit = {
    ...options,
    headers,
    credentials: 'include',
  };

  try {
    const response = await fetch(url, fetchOptions);

    // If 401 Unauthorized occurs on an authenticated endpoint and has not yet retried:
    const isAuthEndpoint = endpoint.includes('/api/auth/login') || endpoint.includes('/api/auth/refresh');
    if (response.status === 401 && !options._retry && !isAuthEndpoint) {
      // Deduplicated token refresh
      const freshToken = await refreshAccessToken();

      if (freshToken) {
        // Retry the original request exactly once with the fresh token
        headers.set('Authorization', `Bearer ${freshToken}`);
        return request<T>(endpoint, {
          ...options,
          headers,
          _retry: true,
        });
      }
    }

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
    throw new ApiClientError(
      'Unable to connect to the server. Please ensure the backend is running.',
      0
    );
  }
}

export const apiClient = {
  request,
  setAccessToken,
  getAccessToken,
  setOnTokenRefreshed,
  setOnAuthFailure,
  refreshAccessToken,

  auth: {
    async login(credentials: LoginCredentials): Promise<LoginResponse> {
      const data = await request<LoginResponse>('/api/auth/login/', {
        method: 'POST',
        body: JSON.stringify(credentials),
      });
      setAccessToken(data.access);
      return data;
    },

    async refreshToken(explicitToken?: string): Promise<{ access: string }> {
      const token = await refreshAccessToken(explicitToken);
      if (!token) {
        throw new ApiClientError('Session expired. Please log in again.', 401);
      }
      return { access: token };
    },

    async getMe(): Promise<UserProfile> {
      return request<UserProfile>('/api/auth/me/', {
        method: 'GET',
      });
    },

    async logout(): Promise<void> {
      try {
        await request<{ success: boolean }>('/api/auth/logout/', {
          method: 'POST',
        });
      } finally {
        setAccessToken(null);
      }
    },
  },
};
