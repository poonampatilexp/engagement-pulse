import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DashboardPreview from '@/components/dashboard/DashboardPreview';
import { AuthProvider } from '@/context/AuthContext';
import { apiClient } from '@/lib/api-client';
import { Project, Risk } from '@/types/project';
import { UserProfile, OrganisationRef } from '@/types/auth';

jest.mock('next/navigation', () => ({
  usePathname: jest.fn().mockReturnValue('/'),
  useRouter: jest.fn().mockReturnValue({ push: jest.fn(), replace: jest.fn() }),
}));

// Mock WebSocket hook to avoid connecting real sockets in unit tests
jest.mock('@/hooks/useOrganisationUpdates', () => ({
  useOrganisationUpdates: jest.fn(),
  getWebSocketBaseUrl: jest.fn().mockReturnValue('ws://localhost:8000'),
}));

describe('DashboardPreview Risk Changes & Maximum Update Depth Prevention', () => {
  let queryClient: QueryClient;

  const mockProject: Project = {
    id: 101,
    organisation: 1,
    name: 'Alpha Project',
    risk_score: 25,
    created_at: '2026-10-31T00:00:00Z',
    updated_at: '2026-10-31T00:00:00Z',
  };

  const initialRisks: Risk[] = [
    {
      id: 501,
      project: 101,
      title: 'Database Latency Issue',
      description: 'Slow queries during peak hours',
      severity: 'high',
      status: 'open',
      owner: 'Alice DB',
      created_at: '2026-10-31T00:00:00Z',
      updated_at: '2026-10-31T00:00:00Z',
    },
    {
      id: 502,
      project: 101,
      title: 'Auth Token Expiry Edge Case',
      description: 'Token refresh occasionally fails',
      severity: 'medium',
      status: 'mitigating',
      owner: 'Bob Security',
      created_at: '2026-10-31T00:00:00Z',
      updated_at: '2026-10-31T00:00:00Z',
    },
  ];

  const mockOrganisations: OrganisationRef[] = [
    { id: 1, name: 'Acme Corp', slug: 'acme-corp' },
  ];

  const mockConsultant: UserProfile = {
    id: 1,
    email: 'consultant@acme.com',
    name: 'Alice Consultant',
    role: 'consultant',
    organisation: null,
    organisations: mockOrganisations,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    jest.spyOn(apiClient.auth, 'refreshToken').mockResolvedValue({ access: 'valid-token' });
    jest.spyOn(apiClient.auth, 'getMe').mockResolvedValue(mockConsultant);
    jest.spyOn(apiClient.organisations, 'list').mockResolvedValue(mockOrganisations);
    jest.spyOn(apiClient.projects, 'list').mockResolvedValue([mockProject]);
    jest.spyOn(apiClient.risks, 'list').mockResolvedValue([...initialRisks]);
  });

  const renderDashboard = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <DashboardPreview />
        </AuthProvider>
      </QueryClientProvider>
    );

  it('renders projects and open risks without exceeding maximum update depth', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    renderDashboard();

    // Verify projects table and open risks card render
    await waitFor(() => {
      expect(screen.getByText('Alpha Project')).toBeInTheDocument();
      expect(screen.getByTestId('open-risks-card')).toBeInTheDocument();
    });

    // Check no Maximum update depth exceeded error
    const maxDepthError = errorSpy.mock.calls.find((call) =>
      call.some((arg) => typeof arg === 'string' && arg.includes('Maximum update depth exceeded'))
    );
    expect(maxDepthError).toBeUndefined();

    errorSpy.mockRestore();
  });

  it('opens drawer and updates risk without triggering infinite re-render loops', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    renderDashboard();

    // Wait for project data to load
    await waitFor(() => {
      expect(screen.getByText('Alpha Project')).toBeInTheDocument();
    });

    // Click on Open Risks card to open drawer
    const openRisksCard = screen.getByTestId('open-risks-card');
    fireEvent.click(openRisksCard);

    // Verify drawer displays the risks
    await waitFor(() => {
      expect(screen.getByText('Database Latency Issue')).toBeInTheDocument();
      expect(screen.getByText('Auth Token Expiry Edge Case')).toBeInTheDocument();
    });

    // Click "Edit" on the first risk
    const editButtons = screen.getAllByRole('button', { name: /edit/i });
    expect(editButtons.length).toBeGreaterThan(0);
    fireEvent.click(editButtons[0]);

    // Verify Edit dialog opens
    await waitFor(() => {
      expect(screen.getByText('Edit Risk Details')).toBeInTheDocument();
    });

    // Mock risk update API response
    const updatedRisk: Risk = {
      ...initialRisks[0],
      title: 'Database Latency Issue - Resolved Indexing',
      status: 'mitigating',
      updated_at: '2026-11-10T12:00:00Z',
    };
    jest.spyOn(apiClient.risks, 'update').mockResolvedValue(updatedRisk);

    // Mock subsequent list calls returning the updated list
    jest.spyOn(apiClient.risks, 'list').mockResolvedValue([updatedRisk, initialRisks[1]]);

    // Submit edit form
    const saveButton = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveButton);

    // Verify drawer reflects updated risk data stably
    await waitFor(() => {
      expect(screen.getByText('Database Latency Issue - Resolved Indexing')).toBeInTheDocument();
    });

    // Verify no Maximum update depth exceeded error occurred
    const maxDepthError = errorSpy.mock.calls.find((call) =>
      call.some((arg) => typeof arg === 'string' && arg.includes('Maximum update depth exceeded'))
    );
    expect(maxDepthError).toBeUndefined();

    errorSpy.mockRestore();
  });

  it('handles query invalidation on risk changes while drawer is open cleanly', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Alpha Project')).toBeInTheDocument();
    });

    // Open project-specific risks drawer via project chip
    const projectRisksChip = screen.getByTestId('project-open-risks-101');
    fireEvent.click(projectRisksChip);

    await waitFor(() => {
      expect(screen.getByText('Open Risks — Alpha Project')).toBeInTheDocument();
      expect(screen.getByText('Database Latency Issue')).toBeInTheDocument();
    });

    // Simulate external live update / query invalidation
    queryClient.invalidateQueries({ queryKey: ['risks'] });
    queryClient.invalidateQueries({ queryKey: ['projects'] });

    // Drawer should still render stably without crashing
    await waitFor(() => {
      expect(screen.getByText('Database Latency Issue')).toBeInTheDocument();
    });

    const maxDepthError = errorSpy.mock.calls.find((call) =>
      call.some((arg) => typeof arg === 'string' && arg.includes('Maximum update depth exceeded'))
    );
    expect(maxDepthError).toBeUndefined();

    errorSpy.mockRestore();
  });
});

