import {
    LoginCredentials,
    LoginResponse,
    UserProfile,
    OrganisationRef,
} from "@/types/auth";
import {
    Project,
    Risk,
    UpdateRiskPayload,
    CSVImportJob,
} from "@/types/project";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const STATUS_MESSAGES: Record<number, string> = {
    401: "Invalid email or password. Please verify your credentials.",
    403: "Access denied. You do not have permission for this resource.",
    404: "Resource not found.",
};

export class ApiClientError extends Error {
    status: number;
    details?: Record<string, any>;

    constructor(message: string, status = 500, details?: Record<string, any>) {
        super(message);
        this.name = "ApiClientError";
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

export function setOnTokenRefreshed(
    callback: ((token: string) => void) | null,
): void {
    onTokenRefreshedCallback = callback;
}

export function setOnAuthFailure(callback: (() => void) | null): void {
    onAuthFailureCallback = callback;
}

/**
 * Executes a token refresh with deduplication.
 * Multiple concurrent callers receive the same pending promise to prevent duplicate refresh calls.
 */
export async function refreshAccessToken(
    explicitToken?: string,
    options?: { notifyOnFailure?: boolean },
): Promise<string | null> {
    if (refreshPromise) {
        return refreshPromise;
    }

    const notifyOnFailure = options?.notifyOnFailure ?? true;

    refreshPromise = (async () => {
        try {
            const body = explicitToken
                ? JSON.stringify({ refresh: explicitToken })
                : undefined;
            const response = await fetch(`${API_BASE}/api/auth/refresh/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "include",
                body,
            });

            if (!response.ok) {
                inMemoryAccessToken = null;
                if (notifyOnFailure) {
                    onAuthFailureCallback?.();
                }
                return null;
            }

            const data = await response.json();
            const newAccessToken = data.access;
            inMemoryAccessToken = newAccessToken;
            onTokenRefreshedCallback?.(newAccessToken);
            return newAccessToken;
        } catch (err) {
            inMemoryAccessToken = null;
            if (notifyOnFailure) {
                onAuthFailureCallback?.();
            }
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

export async function request<T>(
    endpoint: string,
    options: ExtendedRequestInit = {},
): Promise<T> {
    const url = `${API_BASE}${endpoint}`;

    const headers = new Headers(options.headers || {});
    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
        headers.set("Content-Type", "application/json");
    }

    // Attach in-memory JWT bearer token if available and not already set
    if (inMemoryAccessToken && !headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${inMemoryAccessToken}`);
    }

    const fetchOptions: ExtendedRequestInit = {
        ...options,
        headers,
        credentials: "include",
    };

    try {
        const response = await fetch(url, fetchOptions);

        // If 401 Unauthorized occurs on an authenticated endpoint and has not yet retried:
        const isAuthEndpoint =
            endpoint.includes("/api/auth/login") ||
            endpoint.includes("/api/auth/refresh");
        if (response.status === 401 && !options._retry && !isAuthEndpoint) {
            // Deduplicated token refresh
            const freshToken = await refreshAccessToken();

            if (freshToken) {
                // Retry the original request exactly once with the fresh token
                headers.set("Authorization", `Bearer ${freshToken}`);
                return request<T>(endpoint, {
                    ...options,
                    headers,
                    _retry: true,
                });
            }
        }

        const isJson = response.headers
            .get("content-type")
            ?.includes("application/json");
        const data = isJson ? await response.json() : null;

        if (!response.ok) {
            const errorMessage =
                data?.detail ??
                data?.message ??
                data?.non_field_errors?.[0] ??
                data?.email?.[0] ??
                data?.password?.[0] ??
                data?.file?.[0] ??
                STATUS_MESSAGES[response.status] ??
                "An unexpected error occurred. Please try again.";

            throw new ApiClientError(errorMessage, response.status, data);
        }

        return data as T;
    } catch (error: any) {
        if (error instanceof ApiClientError) {
            throw error;
        }
        throw new ApiClientError(
            "Unable to connect to the server. Please ensure the backend is running.",
            0,
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
            const data = await request<any>("/api/auth/login/", {
                method: "POST",
                body: JSON.stringify(credentials),
            });
            const token = data.access_token || data.access;
            setAccessToken(token);
            let user = data.user;
            if (!user) {
                user = await apiClient.auth.getMe();
            }
            return {
                access: token,
                refresh: data.refresh || "",
                user,
            };
        },

        async refreshToken(
            explicitToken?: string,
            options?: { notifyOnFailure?: boolean },
        ): Promise<{ access: string }> {
            const token = await refreshAccessToken(explicitToken, options);
            if (!token) {
                throw new ApiClientError(
                    "Session expired. Please log in again.",
                    401,
                );
            }
            return { access: token };
        },

        async getMe(): Promise<UserProfile> {
            const data = await request<any>("/api/auth/me/", {
                method: "GET",
            });
            return {
                id: data.id,
                email: data.email,
                name:
                    data.name ||
                    data.email
                        .split("@")[0]
                        .replace(".", " ")
                        .replace(/\b\w/g, (c: string) => c.toUpperCase()),
                role: data.role,
                organisation: data.organisation || null,
                organisations: data.organisations || null,
            };
        },

        async getWebSocketTicket(): Promise<{
            ticket: string;
            expires_in: number;
        }> {
            return request<{ ticket: string; expires_in: number }>(
                "/api/auth/ws-ticket/",
                {
                    method: "POST",
                },
            );
        },

        async logout(): Promise<void> {
            try {
                await request<{ success: boolean }>("/api/auth/logout/", {
                    method: "POST",
                });
            } finally {
                setAccessToken(null);
            }
        },
    },

    organisations: {
        async list(): Promise<OrganisationRef[]> {
            return request<OrganisationRef[]>("/api/organisations/", {
                method: "GET",
            });
        },
    },

    projects: {
        async list(organisationId: number): Promise<Project[]> {
            const data = await request<any[]>(
                `/api/organisations/${organisationId}/projects/`,
                {
                    method: "GET",
                },
            );
            return data.map((p) => ({
                ...p,
                organisation: p.organisation ?? p.organisation_id,
                organisation_id: p.organisation_id ?? p.organisation,
            }));
        },
    },

    risks: {
        async list(projectId: number): Promise<Risk[]> {
            const data = await request<any[]>(
                `/api/projects/${projectId}/risks/`,
                {
                    method: "GET",
                },
            );
            return data.map((r) => ({
                ...r,
                project: r.project ?? r.project_id,
                project_id: r.project_id ?? r.project,
            }));
        },

        async update(riskId: number, data: UpdateRiskPayload): Promise<Risk> {
            const updated = await request<any>(`/api/risks/${riskId}/`, {
                method: "PATCH",
                body: JSON.stringify(data),
            });
            return {
                ...updated,
                project: updated.project ?? updated.project_id,
                project_id: updated.project_id ?? updated.project,
            };
        },
    },

    csvJobs: {
        async upload(projectId: number, file: File): Promise<CSVImportJob> {
            const formData = new FormData();
            formData.append("file", file);
            return request<CSVImportJob>(
                `/api/projects/${projectId}/csv-jobs/`,
                {
                    method: "POST",
                    body: formData,
                },
            );
        },

        async getStatus(jobId: string): Promise<CSVImportJob> {
            return request<CSVImportJob>(`/api/csv-jobs/${jobId}/`, {
                method: "GET",
            });
        },
    },
};
