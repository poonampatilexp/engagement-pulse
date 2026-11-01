import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CSVImportDialog from '@/components/dashboard/CSVImportDialog';
import DashboardPreview from '@/components/dashboard/DashboardPreview';
import { AuthProvider } from '@/context/AuthContext';
import { apiClient } from '@/lib/api-client';
import { Project, CSVImportJob } from '@/types/project';
import { UserProfile, OrganisationRef } from '@/types/auth';

jest.mock('next/navigation', () => ({
  usePathname: jest.fn().mockReturnValue('/'),
  useRouter: jest.fn().mockReturnValue({ push: jest.fn(), replace: jest.fn() }),
}));

describe('Background CSV Job with Status Frontend', () => {
  let queryClient: QueryClient;

  const mockProject: Project = {
    id: 101,
    organisation: 1,
    name: 'Apollo Mission Upgrade',
    risk_score: 25,
    created_at: '2026-10-31T00:00:00Z',
    updated_at: '2026-10-31T00:00:00Z',
  };

  const mockOrganisations: OrganisationRef[] = [
    { id: 1, name: 'NASA', slug: 'nasa' },
  ];

  const mockConsultant: UserProfile = {
    id: 1,
    email: 'consultant@engagementpulse.com',
    name: 'Alice Consultant',
    role: 'consultant',
    organisation: null,
    organisations: mockOrganisations,
  };

  const mockViewer: UserProfile = {
    id: 2,
    email: 'viewer@nasa.gov',
    name: 'Bob Viewer',
    role: 'client_viewer',
    organisation: { id: 1, name: 'NASA', slug: 'nasa' },
    organisations: null,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    jest.spyOn(apiClient.auth, 'refreshToken').mockResolvedValue({ access: 'valid-access-token' });
    jest.spyOn(apiClient.organisations, 'list').mockResolvedValue(mockOrganisations);
    jest.spyOn(apiClient.projects, 'list').mockResolvedValue([mockProject]);
    jest.spyOn(apiClient.risks, 'list').mockResolvedValue([]);
  });

  const renderWithProviders = (ui: React.ReactElement) =>
    render(
      <QueryClientProvider client={queryClient}>
        {ui}
      </QueryClientProvider>
    );

  const renderDashboardWithAuth = (user: UserProfile) => {
    jest.spyOn(apiClient.auth, 'getMe').mockResolvedValue(user);

    return render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <DashboardPreview />
        </AuthProvider>
      </QueryClientProvider>
    );
  };

  describe('Role-based Visibility on Dashboard', () => {
    it('displays Import CSV button on project rows for an authorised Consultant', async () => {
      renderDashboardWithAuth(mockConsultant);

      await waitFor(() => {
        expect(screen.getByText('Apollo Mission Upgrade')).toBeInTheDocument();
      });

      const importBtn = screen.getByTestId('import-csv-btn-101');
      expect(importBtn).toBeInTheDocument();
      expect(importBtn).toHaveTextContent(/import csv/i);
    });

    it('hides all Import CSV buttons from Client Viewers', async () => {
      renderDashboardWithAuth(mockViewer);

      await waitFor(() => {
        expect(screen.getByText('Apollo Mission Upgrade')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('import-csv-btn-101')).not.toBeInTheDocument();
      expect(screen.queryByText(/import csv/i)).not.toBeInTheDocument();
    });
  });

  describe('CSVImportDialog Workflow', () => {
    it('allows selecting a CSV file and uploading it, displaying returned job ID and status', async () => {
      const mockQueuedJob: CSVImportJob = {
        id: 'job-uuid-1234',
        job_id: 'job-uuid-1234',
        project: 101,
        project_name: 'Apollo Mission Upgrade',
        filename: 'risks.csv',
        status: 'queued',
        total_rows: 0,
        processed_rows: 0,
        error_details: {},
        created_by_email: 'consultant@engagementpulse.com',
        created_at: '2026-11-01T00:00:00Z',
        updated_at: '2026-11-01T00:00:00Z',
      };

      const uploadSpy = jest.spyOn(apiClient.csvJobs, 'upload').mockResolvedValue(mockQueuedJob);
      const getStatusSpy = jest.spyOn(apiClient.csvJobs, 'getStatus').mockResolvedValue(mockQueuedJob);

      renderWithProviders(
        <CSVImportDialog open={true} onClose={jest.fn()} project={mockProject} />
      );

      expect(screen.getByText(/import risks from csv/i)).toBeInTheDocument();
      expect(screen.getByText('Apollo Mission Upgrade')).toBeInTheDocument();

      // Upload button should be disabled before file is selected
      const uploadBtn = screen.getByRole('button', { name: /upload & import/i });
      expect(uploadBtn).toBeDisabled();

      // Select CSV file
      const fileInput = screen.getByTestId('csv-file-input');
      const file = new File(['title,severity\nRisk 1,high\n'], 'risks.csv', { type: 'text/csv' });
      fireEvent.change(fileInput, { target: { files: [file] } });

      // File name should be displayed and button enabled
      expect(screen.getByText(/risks\.csv/i)).toBeInTheDocument();
      expect(uploadBtn).toBeEnabled();

      // Click upload
      fireEvent.click(uploadBtn);

      await waitFor(() => {
        expect(uploadSpy).toHaveBeenCalledWith(101, file);
      });

      // Verifies job ID and Queued status are displayed
      await waitFor(() => {
        expect(screen.getByText('job-uuid-1234')).toBeInTheDocument();
        expect(screen.getByText('Queued')).toBeInTheDocument();
      });

      expect(getStatusSpy).toHaveBeenCalledWith('job-uuid-1234');
    });

    it('polls status and displays completed status with processed rows on success', async () => {
      const mockCompletedJob: CSVImportJob = {
        id: 'job-uuid-5678',
        job_id: 'job-uuid-5678',
        project: 101,
        project_name: 'Apollo Mission Upgrade',
        filename: 'valid_risks.csv',
        status: 'completed',
        total_rows: 5,
        processed_rows: 5,
        error_details: {},
        created_by_email: 'consultant@engagementpulse.com',
        created_at: '2026-11-01T00:00:00Z',
        updated_at: '2026-11-01T00:00:00Z',
      };

      jest.spyOn(apiClient.csvJobs, 'upload').mockResolvedValue({
        ...mockCompletedJob,
        status: 'queued',
      });
      jest.spyOn(apiClient.csvJobs, 'getStatus').mockResolvedValue(mockCompletedJob);

      renderWithProviders(
        <CSVImportDialog open={true} onClose={jest.fn()} project={mockProject} />
      );

      // Select and upload file
      const fileInput = screen.getByTestId('csv-file-input');
      const file = new File(['dummy'], 'valid_risks.csv', { type: 'text/csv' });
      fireEvent.change(fileInput, { target: { files: [file] } });
      fireEvent.click(screen.getByRole('button', { name: /upload & import/i }));

      // Wait for completed status and processed row count
      await waitFor(() => {
        expect(screen.getByText('Completed')).toBeInTheDocument();
        expect(screen.getByText(/import completed successfully! processed 5 of 5 rows\./i)).toBeInTheDocument();
      });

      expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument();
    });

    it('displays error details when the job status is failed', async () => {
      const mockFailedJob: CSVImportJob = {
        id: 'job-uuid-fail',
        job_id: 'job-uuid-fail',
        project: 101,
        project_name: 'Apollo Mission Upgrade',
        filename: 'bad.csv',
        status: 'failed',
        total_rows: 3,
        processed_rows: 0,
        error_details: {
          errors: ["Row 2: Invalid severity 'extreme'. Allowed choices: low, medium, high, critical."],
        },
        created_by_email: 'consultant@engagementpulse.com',
        created_at: '2026-11-01T00:00:00Z',
        updated_at: '2026-11-01T00:00:00Z',
      };

      jest.spyOn(apiClient.csvJobs, 'upload').mockResolvedValue({
        ...mockFailedJob,
        status: 'queued',
      });
      jest.spyOn(apiClient.csvJobs, 'getStatus').mockResolvedValue(mockFailedJob);

      renderWithProviders(
        <CSVImportDialog open={true} onClose={jest.fn()} project={mockProject} />
      );

      // Select and upload file
      const fileInput = screen.getByTestId('csv-file-input');
      const file = new File(['dummy'], 'bad.csv', { type: 'text/csv' });
      fireEvent.change(fileInput, { target: { files: [file] } });
      fireEvent.click(screen.getByRole('button', { name: /upload & import/i }));

      // Wait for failed status and error details
      await waitFor(() => {
        expect(screen.getByText('Failed')).toBeInTheDocument();
        expect(screen.getByText(/import failed\./i)).toBeInTheDocument();
        expect(screen.getByText(/Row 2: Invalid severity 'extreme'/i)).toBeInTheDocument();
      });
    });

    it('enforces client-side 10MB file size limit', async () => {
      renderWithProviders(
        <CSVImportDialog open={true} onClose={jest.fn()} project={mockProject} />
      );

      const fileInput = screen.getByTestId('csv-file-input');
      const largeFile = new File(['x'.repeat(100)], 'large.csv', { type: 'text/csv' });
      Object.defineProperty(largeFile, 'size', { value: 11 * 1024 * 1024 });

      fireEvent.change(fileInput, { target: { files: [largeFile] } });

      expect(screen.getByText(/file size exceeds the 10mb limit/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /upload & import/i })).toBeDisabled();
    });

    it('prevents closing and shows in-progress notice while job is actively running', async () => {
      const mockRunningJob: CSVImportJob = {
        id: 'job-uuid-running',
        job_id: 'job-uuid-running',
        project: 101,
        project_name: 'Apollo Mission Upgrade',
        filename: 'risks.csv',
        status: 'processing',
        total_rows: 10,
        processed_rows: 3,
        error_details: {},
        created_by_email: 'consultant@engagementpulse.com',
        created_at: '2026-11-01T00:00:00Z',
        updated_at: '2026-11-01T00:00:00Z',
      };

      jest.spyOn(apiClient.csvJobs, 'upload').mockResolvedValue(mockRunningJob);
      jest.spyOn(apiClient.csvJobs, 'getStatus').mockResolvedValue(mockRunningJob);

      const onCloseMock = jest.fn();
      renderWithProviders(
        <CSVImportDialog open={true} onClose={onCloseMock} project={mockProject} />
      );

      const fileInput = screen.getByTestId('csv-file-input');
      const file = new File(['title\nrisk1'], 'risks.csv', { type: 'text/csv' });
      fireEvent.change(fileInput, { target: { files: [file] } });
      fireEvent.click(screen.getByRole('button', { name: /upload & import/i }));

      await waitFor(() => {
        expect(screen.getByText(/import in progress\.\.\. closing disabled/i)).toBeInTheDocument();
      });

      expect(screen.queryByRole('button', { name: /done/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
      expect(onCloseMock).not.toHaveBeenCalled();
    });

    it('displays a clear error if polling the job status API fails', async () => {
      const mockQueuedJob: CSVImportJob = {
        id: 'job-uuid-poll-fail',
        job_id: 'job-uuid-poll-fail',
        project: 101,
        project_name: 'Apollo Mission Upgrade',
        filename: 'risks.csv',
        status: 'queued',
        total_rows: 0,
        processed_rows: 0,
        error_details: {},
        created_by_email: 'consultant@engagementpulse.com',
        created_at: '2026-11-01T00:00:00Z',
        updated_at: '2026-11-01T00:00:00Z',
      };

      jest.spyOn(apiClient.csvJobs, 'upload').mockResolvedValue(mockQueuedJob);
      jest.spyOn(apiClient.csvJobs, 'getStatus').mockRejectedValue(new Error('Network error polling status'));

      renderWithProviders(
        <CSVImportDialog open={true} onClose={jest.fn()} project={mockProject} />
      );

      const fileInput = screen.getByTestId('csv-file-input');
      const file = new File(['title\nrisk1'], 'risks.csv', { type: 'text/csv' });
      fireEvent.change(fileInput, { target: { files: [file] } });
      fireEvent.click(screen.getByRole('button', { name: /upload & import/i }));

      await waitFor(() => {
        expect(screen.getByText(/failed to retrieve job status/i)).toBeInTheDocument();
        expect(screen.getByText(/network error polling status/i)).toBeInTheDocument();
      });
    });
  });
});
