import {
  apiClient,
  setAccessToken,
  getAccessToken,
  setOnAuthFailure,
  setOnTokenRefreshed,
  ApiClientError,
} from '@/lib/api-client';

describe('API Client & Session Management', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    setAccessToken(null);
    setOnAuthFailure(null);
    setOnTokenRefreshed(null);
    jest.clearAllMocks();
  });

  afterAll(() => {
    global.fetch = originalFetch;
  });

  test('attaches in-memory Authorization bearer token when present', async () => {
    setAccessToken('mock-access-token');

    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ data: 'success' }),
    });
    global.fetch = mockFetch;

    const result = await apiClient.request('/api/organisations/');
    expect(result).toEqual({ data: 'success' });
    expect(mockFetch).toHaveBeenCalledTimes(1);

    const callHeaders = mockFetch.mock.calls[0][1].headers;
    expect(callHeaders.get('Authorization')).toBe('Bearer mock-access-token');
  });

  test('transparently refreshes token on 401 and retries original request', async () => {
    setAccessToken('expired-access-token');

    let requestCount = 0;
    const mockFetch = jest.fn().mockImplementation(async (url: string) => {
      if (url.includes('/api/auth/refresh')) {
        return {
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ access: 'new-fresh-access-token' }),
        };
      }

      if (url.includes('/api/projects/')) {
        requestCount++;
        if (requestCount === 1) {
          // First attempt fails with 401
          return {
            ok: false,
            status: 401,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({ detail: 'Given token not valid for any token type' }),
          };
        }
        // Second attempt with new token succeeds
        return {
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => [{ id: 1, name: 'ERP Modernisation' }],
        };
      }

      return { ok: false, status: 404 };
    });

    global.fetch = mockFetch;

    const result = await apiClient.request('/api/projects/');
    expect(result).toEqual([{ id: 1, name: 'ERP Modernisation' }]);
    expect(getAccessToken()).toBe('new-fresh-access-token');
    // 1st request -> 401, 2nd request -> refresh, 3rd request -> retry
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  test('deduplicates multiple concurrent requests so only one refresh call is made', async () => {
    setAccessToken('expired-access-token');

    let refreshCallCount = 0;
    const mockFetch = jest.fn().mockImplementation(async (url: string) => {
      if (url.includes('/api/auth/refresh')) {
        refreshCallCount++;
        // Small delay to simulate network latency
        await new Promise((resolve) => setTimeout(resolve, 50));
        return {
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ access: 'concurrent-fresh-token' }),
        };
      }

      // Initial call returns 401; retried call returns success
      const headers = mockFetch.mock.calls[mockFetch.mock.calls.length - 1]?.[1]?.headers;
      const isRetried = headers?.get('Authorization') === 'Bearer concurrent-fresh-token';

      if (!isRetried) {
        return {
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'Token expired' }),
        };
      }

      return {
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, url }),
      };
    });

    global.fetch = mockFetch;

    // Fire 3 simultaneous API requests
    const [res1, res2, res3] = await Promise.all([
      apiClient.request('/api/projects/'),
      apiClient.request('/api/organisations/'),
      apiClient.request('/api/auth/me/'),
    ]);

    expect(res1).toBeDefined();
    expect(res2).toBeDefined();
    expect(res3).toBeDefined();

    // Exactly 1 refresh call was made across all 3 concurrent requests
    expect(refreshCallCount).toBe(1);
    expect(getAccessToken()).toBe('concurrent-fresh-token');
  });

  test('clears auth state and triggers onAuthFailure when refresh fails', async () => {
    setAccessToken('invalid-token');
    const authFailureSpy = jest.fn();
    setOnAuthFailure(authFailureSpy);

    const mockFetch = jest.fn().mockImplementation(async (url: string) => {
      if (url.includes('/api/auth/refresh')) {
        return {
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'Token is invalid or expired' }),
        };
      }

      return {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Authentication required' }),
      };
    });

    global.fetch = mockFetch;

    await expect(apiClient.request('/api/projects/')).rejects.toThrow(ApiClientError);
    expect(getAccessToken()).toBeNull();
    expect(authFailureSpy).toHaveBeenCalledTimes(1);
  });

  test('logout clears in-memory token and sends logout request', async () => {
    setAccessToken('active-token');

    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ success: true }),
    });
    global.fetch = mockFetch;

    await apiClient.auth.logout();
    expect(getAccessToken()).toBeNull();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/auth/logout/'),
      expect.objectContaining({ method: 'POST' })
    );
  });
});

