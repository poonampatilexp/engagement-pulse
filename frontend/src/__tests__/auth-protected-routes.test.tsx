import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { usePathname, useRouter } from 'next/navigation';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AppShell from '@/components/layout/AppShell';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { apiClient } from '@/lib/api-client';

// Mock Next.js navigation hooks
jest.mock('next/navigation', () => ({
  usePathname: jest.fn(),
  useRouter: jest.fn(),
}));

describe('Protected Routes & Session Guard', () => {
  const mockPush = jest.fn();
  const mockReplace = jest.fn();
  let queryClient: QueryClient;

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      replace: mockReplace,
    });
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.spyOn(apiClient.organisations, 'list').mockResolvedValue([
      { id: 1, name: 'Acme Corp', slug: 'acme' },
    ]);
  });

  const renderWithProviders = (ui: React.ReactNode) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>{ui}</AuthProvider>
      </QueryClientProvider>
    );
  };

  test('shows loading indicator while resolving authentication and does NOT expose protected content', async () => {
    (usePathname as jest.Mock).mockReturnValue('/');

    // Refresh request stays pending
    jest.spyOn(apiClient.auth, 'refreshToken').mockImplementation(
      () => new Promise(() => {})
    );

    renderWithProviders(
      <AppShell>
        <div data-testid="protected-content">Confidential Project Dashboard</div>
      </AppShell>
    );

    // Verifying session loading indicator is visible
    expect(screen.getByTestId('auth-loading-state')).toBeInTheDocument();
    expect(screen.getByText(/Authenticating session.../i)).toBeInTheDocument();

    // Protected content is NOT rendered during loading
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  test('redirects unauthenticated user from protected dashboard to /login', async () => {
    (usePathname as jest.Mock).mockReturnValue('/');

    // Session restoration fails (unauthenticated / no cookie)
    jest.spyOn(apiClient.auth, 'refreshToken').mockRejectedValue(new Error('No token'));

    renderWithProviders(
      <AppShell>
        <div data-testid="protected-content">Confidential Project Dashboard</div>
      </AppShell>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login');
    });

    // Content was never rendered
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  test('redirects authenticated user away from /login to /', async () => {
    (usePathname as jest.Mock).mockReturnValue('/login');

    // Simulate successful session restoration
    jest.spyOn(apiClient.auth, 'refreshToken').mockResolvedValue({ access: 'valid-token' });
    jest.spyOn(apiClient.auth, 'getMe').mockResolvedValue({
      id: 1,
      name: 'Alice Consultant',
      email: 'consultant@engagementpulse.com',
      role: 'consultant',
      organisation: null,
      organisations: [{ id: 1, name: 'Acme Corp', slug: 'acme' }],
    });

    renderWithProviders(
      <AppShell>
        <div data-testid="login-form">Login Page Form</div>
      </AppShell>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/');
    });

    expect(screen.queryByTestId('login-form')).not.toBeInTheDocument();
  });

  test('allows unauthenticated user to view /login page', async () => {
    (usePathname as jest.Mock).mockReturnValue('/login');

    jest.spyOn(apiClient.auth, 'refreshToken').mockRejectedValue(new Error('No cookie'));

    renderWithProviders(
      <AppShell>
        <div data-testid="login-form">Login Page Form</div>
      </AppShell>
    );

    await waitFor(() => {
      expect(screen.getByTestId('login-form')).toBeInTheDocument();
    });

    expect(mockReplace).not.toHaveBeenCalled();
  });

  test('renders dashboard shell and user profile for authenticated consultant', async () => {
    (usePathname as jest.Mock).mockReturnValue('/');

    jest.spyOn(apiClient.auth, 'refreshToken').mockResolvedValue({ access: 'valid-token' });
    jest.spyOn(apiClient.auth, 'getMe').mockResolvedValue({
      id: 1,
      name: 'Alice Consultant',
      email: 'consultant@engagementpulse.com',
      role: 'consultant',
      organisation: null,
      organisations: [
        { id: 1, name: 'Acme Corp', slug: 'acme' },
        { id: 2, name: 'Globex Corp', slug: 'globex' },
      ],
    });

    renderWithProviders(
      <AppShell>
        <div data-testid="dashboard-content">Dashboard Metrics</div>
      </AppShell>
    );

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-content')).toBeInTheDocument();
    });

    // Consultant details visible in Header
    expect(screen.getByText('Alice Consultant')).toBeInTheDocument();
    expect(screen.getAllByText(/consultant/i).length).toBeGreaterThan(1);
    expect(screen.getAllByText('Acme Corp').length).toBeGreaterThan(0);
  });

  test('renders dashboard shell and role for authenticated client viewer', async () => {
    (usePathname as jest.Mock).mockReturnValue('/');

    jest.spyOn(apiClient.auth, 'refreshToken').mockResolvedValue({ access: 'valid-token' });
    jest.spyOn(apiClient.auth, 'getMe').mockResolvedValue({
      id: 2,
      name: 'Bob Acme Viewer',
      email: 'viewer.acme@example.com',
      role: 'client_viewer',
      organisation: { id: 1, name: 'Acme Corp', slug: 'acme' },
      organisations: null,
    });

    renderWithProviders(
      <AppShell>
        <div data-testid="dashboard-content">Dashboard Metrics</div>
      </AppShell>
    );

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-content')).toBeInTheDocument();
    });

    // Client Viewer details visible in Header
    expect(screen.getByText('Bob Acme Viewer')).toBeInTheDocument();
    expect(screen.getByText(/client viewer/i)).toBeInTheDocument();
  });

  test('logout clears auth state, clears react query cache, and redirects to /login', async () => {
    (usePathname as jest.Mock).mockReturnValue('/');

    jest.spyOn(apiClient.auth, 'refreshToken').mockResolvedValue({ access: 'valid-token' });
    jest.spyOn(apiClient.auth, 'getMe').mockResolvedValue({
      id: 1,
      name: 'Alice Consultant',
      email: 'consultant@engagementpulse.com',
      role: 'consultant',
      organisation: null,
      organisations: [{ id: 1, name: 'Acme Corp', slug: 'acme' }],
    });
    const logoutApiSpy = jest.spyOn(apiClient.auth, 'logout').mockResolvedValue(undefined);
    const clearQueryCacheSpy = jest.spyOn(queryClient, 'clear');

    let capturedLogout: (() => Promise<void>) | null = null;
    function TestConsumer() {
      const { logout } = useAuth();
      capturedLogout = logout;
      return <div>Consumer</div>;
    }

    renderWithProviders(
      <AppShell>
        <TestConsumer />
      </AppShell>
    );

    await waitFor(() => {
      expect(screen.getByText('Alice Consultant')).toBeInTheDocument();
    });

    // Execute logout wrapped in act
    await act(async () => {
      await capturedLogout!();
    });

    expect(logoutApiSpy).toHaveBeenCalledTimes(1);
    expect(clearQueryCacheSpy).toHaveBeenCalledTimes(1);
    expect(mockReplace).toHaveBeenCalledWith('/login');
  });
});


