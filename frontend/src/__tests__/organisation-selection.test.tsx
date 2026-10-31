import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Header from '@/components/layout/Header';
import DashboardPreview from '@/components/dashboard/DashboardPreview';
import { AuthProvider } from '@/context/AuthContext';
import { apiClient } from '@/lib/api-client';
import { Project, Risk } from '@/types/project';
import { OrganisationRef } from '@/types/auth';

jest.mock('next/navigation', () => ({
  usePathname: jest.fn().mockReturnValue('/'),
  useRouter: jest.fn().mockReturnValue({ push: jest.fn(), replace: jest.fn() }),
}));

describe('Organisation Selection & Multi-Tenant Switching', () => {
  let queryClient: QueryClient;

  const mockOrganisations: OrganisationRef[] = [
    { id: 1, name: 'Acme Corp', slug: 'acme-corp' },
    { id: 2, name: 'Globex Corporation', slug: 'globex-corp' },
  ];

  const acmeProjects: Project[] = [
    {
      id: 1,
      organisation: 1,
      name: 'Acme ERP Modernisation',
      risk_score: 13,
      created_at: '2026-10-31T00:00:00Z',
      updated_at: '2026-10-31T00:00:00Z',
    },
  ];

  const globexProjects: Project[] = [
    {
      id: 2,
      organisation: 2,
      name: 'Globex Cloud Infrastructure',
      risk_score: 12,
      created_at: '2026-10-31T00:00:00Z',
      updated_at: '2026-10-31T00:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    jest.spyOn(apiClient.organisations, 'list').mockResolvedValue(mockOrganisations);
    jest.spyOn(apiClient.projects, 'list').mockImplementation(async (orgId) => {
      if (orgId === 1) return acmeProjects;
      if (orgId === 2) return globexProjects;
      return [];
    });
    jest.spyOn(apiClient.risks, 'list').mockResolvedValue([]);
  });

  const renderApp = (role: 'consultant' | 'client_viewer' = 'consultant') => {
    jest.spyOn(apiClient.auth, 'refreshToken').mockResolvedValue({ access: 'valid-token' });
    jest.spyOn(apiClient.auth, 'getMe').mockResolvedValue({
      id: role === 'consultant' ? 1 : 2,
      name: role === 'consultant' ? 'Alice Consultant' : 'Bob Acme Viewer',
      email: role === 'consultant' ? 'consultant@engagementpulse.com' : 'viewer.acme@example.com',
      role,
      organisation: role === 'client_viewer' ? { id: 1, name: 'Acme Corp', slug: 'acme-corp' } : null,
      organisations: role === 'consultant' ? mockOrganisations : null,
    });

    return render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <Header onMobileDrawerToggle={jest.fn()} />
          <DashboardPreview />
        </AuthProvider>
      </QueryClientProvider>
    );
  };

  test('fetches organisations from GET /api/organisations/ on authentication', async () => {
    const listSpy = jest.spyOn(apiClient.organisations, 'list');
    renderApp('consultant');

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledTimes(1);
    });
  });

  test('consultant can switch between authorised organisations using the header dropdown', async () => {
    renderApp('consultant');

    // Wait for initial render with Acme Corp
    await waitFor(() => {
      expect(screen.getByText('Acme ERP Modernisation')).toBeInTheDocument();
    });

    const orgChip = screen.getByTestId('organisation-selector-chip');
    expect(orgChip).toHaveTextContent('Acme Corp');

    // Click the organisation chip to open dropdown
    fireEvent.click(orgChip);

    // Dropdown shows both organisations
    await waitFor(() => {
      expect(screen.getByText('Switch Organisation')).toBeInTheDocument();
    });
    expect(screen.getByRole('menuitem', { name: /Globex Corporation/i })).toBeInTheDocument();

    // Select Globex Corporation
    fireEvent.click(screen.getByRole('menuitem', { name: /Globex Corporation/i }));

    // Active organisation updates in the header chip
    await waitFor(() => {
      expect(orgChip).toHaveTextContent('Globex Corporation');
    });

    // Only Globex data is loaded!
    await waitFor(() => {
      expect(screen.getByText('Globex Cloud Infrastructure')).toBeInTheDocument();
    });
    expect(screen.queryByText('Acme ERP Modernisation')).not.toBeInTheDocument();
  });

  test('client viewer sees only assigned organisation without a dropdown menu', async () => {
    // For client viewer, GET /api/organisations/ returns only their single organisation
    jest.spyOn(apiClient.organisations, 'list').mockResolvedValue([
      { id: 1, name: 'Acme Corp', slug: 'acme-corp' },
    ]);

    renderApp('client_viewer');

    await waitFor(() => {
      expect(screen.getByText('Acme ERP Modernisation')).toBeInTheDocument();
    });

    const orgChip = screen.getByTestId('organisation-selector-chip');
    expect(orgChip).toHaveTextContent('Acme Corp');

    // Attempt to click the organisation chip
    fireEvent.click(orgChip);

    // No dropdown menu should appear for client viewer
    expect(screen.queryByText('Switch Organisation')).not.toBeInTheDocument();
  });

  test('clears previous organisation queries when switching organisations', async () => {
    const removeQueriesSpy = jest.spyOn(queryClient, 'removeQueries');
    renderApp('consultant');

    await waitFor(() => {
      expect(screen.getByText('Acme ERP Modernisation')).toBeInTheDocument();
    });

    const orgChip = screen.getByTestId('organisation-selector-chip');
    fireEvent.click(orgChip);

    await waitFor(() => {
      expect(screen.getByRole('menuitem', { name: /Globex Corporation/i })).toBeInTheDocument();
    });

    // Select Globex
    fireEvent.click(screen.getByRole('menuitem', { name: /Globex Corporation/i }));

    // Verifies previous organisation queries were cleared
    expect(removeQueriesSpy).toHaveBeenCalledWith({ queryKey: ['projects'] });
    expect(removeQueriesSpy).toHaveBeenCalledWith({ queryKey: ['risks'] });
  });

  test('clears all organisation and query data on logout', async () => {
    const clearQueryCacheSpy = jest.spyOn(queryClient, 'clear');
    jest.spyOn(apiClient.auth, 'logout').mockResolvedValue();

    renderApp('consultant');

    await waitFor(() => {
      expect(screen.getByText('Acme ERP Modernisation')).toBeInTheDocument();
    });

    // Click Sign Out in Header
    const signOutBtn = screen.getByRole('button', { name: /sign out/i });
    fireEvent.click(signOutBtn);

    await waitFor(() => {
      expect(clearQueryCacheSpy).toHaveBeenCalledTimes(1);
    });
  });
});

