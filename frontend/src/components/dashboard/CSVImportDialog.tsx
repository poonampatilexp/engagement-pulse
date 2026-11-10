'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
  Chip,
  CircularProgress,
} from '@mui/material';
import UploadFileRoundedIcon from '@mui/icons-material/UploadFileRounded';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Project, CSVJobStatus } from '@/types/project';

const MAX_CSV_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB limit matching backend CSVUploadSerializer

interface CSVImportDialogProps {
  open: boolean;
  onClose: () => void;
  project: Project | null;
}

function getStatusChip(status: CSVJobStatus) {
  switch (status) {
    case 'queued':
      return (
        <Chip
          label="Queued"
          size="small"
          sx={{ bgcolor: '#F1F5F9', color: '#475569', fontWeight: 600 }}
        />
      );
    case 'processing':
      return (
        <Chip
          label="Processing"
          size="small"
          icon={<CircularProgress size={14} sx={{ color: '#C2410C !important' }} />}
          sx={{ bgcolor: '#FFEDD5', color: '#C2410C', fontWeight: 600 }}
        />
      );
    case 'completed':
      return (
        <Chip
          label="Completed"
          size="small"
          color="success"
          sx={{ fontWeight: 600 }}
        />
      );
    case 'failed':
      return (
        <Chip
          label="Failed"
          size="small"
          color="error"
          sx={{ fontWeight: 600 }}
        />
      );
    default:
      return null;
  }
}

export default function CSVImportDialog({ open, onClose, project }: CSVImportDialogProps) {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);

  // Preserve active job tracking per project; only clear when switching to a different project
  const prevProjectIdRef = useRef(project?.id);
  const completedJobRef = useRef<string | null>(null);
  useEffect(() => {
    if (project?.id !== prevProjectIdRef.current) {
      prevProjectIdRef.current = project?.id;
      completedJobRef.current = null;
      setSelectedFile(null);
      setActiveJobId(null);
      setClientError(null);
    }
  }, [project?.id]);

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      if (!project) throw new Error('No project selected');
      return apiClient.csvJobs.upload(project.id, file);
    },
    onSuccess: (data) => {
      setActiveJobId(data.id || data.job_id);
      setClientError(null);
    },
    onError: (err: any) => {
      setClientError(err.message || 'Failed to upload CSV file.');
    },
  });

  // Poll job status until completed or failed
  const {
    data: job,
    isError: isPollingError,
    error: pollingError,
  } = useQuery({
    queryKey: ['csv-job', activeJobId],
    queryFn: () => apiClient.csvJobs.getStatus(activeJobId!),
    enabled: !!activeJobId,
    refetchInterval: (query) => {
      const currentStatus = query.state.data?.status;
      if (currentStatus === 'completed' || currentStatus === 'failed') {
        return false; // Stop polling
      }
      return 1000; // Poll every second while queued or processing
    },
  });

  // When job completes, refresh relevant project and risk data without full page reload
  useEffect(() => {
    const currentJobId = job?.id || job?.job_id;
    if (job?.status === 'completed' && project && currentJobId && completedJobRef.current !== currentJobId) {
      completedJobRef.current = currentJobId;
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['risks', project.id] });
      queryClient.invalidateQueries({ queryKey: ['risks'] });
    }
  }, [job?.status, job?.id, job?.job_id, project, queryClient]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.csv')) {
        setClientError('Please select a valid .csv file.');
        setSelectedFile(null);
        return;
      }
      if (file.size === 0) {
        setClientError('The uploaded CSV file is empty.');
        setSelectedFile(null);
        return;
      }
      if (file.size > MAX_CSV_SIZE_BYTES) {
        setClientError('File size exceeds the 10MB limit.');
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setClientError(null);
    }
  };

  const handleUpload = () => {
    if (!selectedFile || !project) return;
    if (selectedFile.size > MAX_CSV_SIZE_BYTES) {
      setClientError('File size exceeds the 10MB limit.');
      return;
    }
    uploadMutation.mutate(selectedFile);
  };

  const isUploading = uploadMutation.isPending;
  const isJobActive = !!activeJobId;
  const currentStatus = job?.status || (isJobActive ? 'queued' : null);
  const isFinished = currentStatus === 'completed' || currentStatus === 'failed';

  const handleClose = () => {
    // 2. Prevent closing while a job is actively queued or processing for this MVP
    if (isJobActive && !isFinished) {
      return;
    }
    // Clean up finished job tracking on explicit close/done
    if (isFinished) {
      setActiveJobId(null);
      setSelectedFile(null);
      setClientError(null);
    }
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={isJobActive && !isFinished ? undefined : handleClose}
      disableEscapeKeyDown={isJobActive && !isFinished}
      maxWidth="sm"
      fullWidth
      aria-labelledby="csv-import-dialog-title"
    >
      <DialogTitle id="csv-import-dialog-title" sx={{ fontWeight: 700, color: '#0F172A' }}>
        Import Risks from CSV
      </DialogTitle>

      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Upload a CSV file of risks for <strong>{project?.name || 'this project'}</strong>.
        </Typography>

        {/* File Picker Section (Shown when no active job) */}
        {!isJobActive && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Button
                component="label"
                variant="outlined"
                startIcon={<UploadFileRoundedIcon />}
                disabled={isUploading}
                sx={{ textTransform: 'none', fontWeight: 600 }}
              >
                Select CSV File
                <input
                  type="file"
                  accept=".csv"
                  hidden
                  onChange={handleFileChange}
                  data-testid="csv-file-input"
                />
              </Button>

              {selectedFile && (
                <Typography variant="body2" sx={{ color: '#0F172A', fontWeight: 500 }}>
                  {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                </Typography>
              )}
            </Box>

            {clientError && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {clientError}
              </Alert>
            )}
          </Box>
        )}

        {/* Job Status & Results Section */}
        {isJobActive && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, p: 2, bgcolor: '#F8FAFC', borderRadius: 2, border: '1px solid #E2E8F0' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box>
                <Typography variant="caption" sx={{ color: '#64748B', display: 'block', textTransform: 'uppercase', fontWeight: 600 }}>
                  Import Job ID
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 600, color: '#0F172A' }}>
                  {activeJobId}
                </Typography>
              </Box>
              {currentStatus && getStatusChip(currentStatus)}
            </Box>

            {/* In-progress status text */}
            {!isFinished && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <CircularProgress size={16} sx={{ color: 'primary.main' }} />
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  {currentStatus === 'queued' ? 'Job is queued for processing...' : 'Worker is importing risks...'}
                </Typography>
              </Box>
            )}

            {/* 1. Display clear error if polling the job status API fails */}
            {isPollingError && (
              <Alert severity="error" sx={{ mt: 1 }}>
                Failed to retrieve job status. {(pollingError as any)?.message || 'Please check your connection and try again.'}
              </Alert>
            )}

            {/* Success message */}
            {currentStatus === 'completed' && (
              <Alert severity="success" sx={{ mt: 1 }}>
                Import completed successfully! Processed {job?.processed_rows ?? 0} of {job?.total_rows ?? 0} rows.
              </Alert>
            )}

            {/* Failure message */}
            {currentStatus === 'failed' && (
              <Alert severity="error" sx={{ mt: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Import failed.
                </Typography>
                {job?.error_details?.errors && job.error_details.errors.length > 0 && (
                  <Box component="ul" sx={{ pl: 2.5, m: 0, mt: 0.5 }}>
                    {job.error_details.errors.map((err: string, i: number) => (
                      <li key={i}>
                        <Typography variant="caption">{err}</Typography>
                      </li>
                    ))}
                  </Box>
                )}
              </Alert>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2.5 }}>
        {!isJobActive ? (
          <>
            <Button onClick={onClose} disabled={isUploading} sx={{ textTransform: 'none' }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleUpload}
              disabled={!selectedFile || isUploading}
              startIcon={isUploading ? <CircularProgress size={16} color="inherit" /> : null}
              sx={{ textTransform: 'none', fontWeight: 600 }}
            >
              {isUploading ? 'Uploading...' : 'Upload & Import'}
            </Button>
          </>
        ) : (
          <>
            {isFinished ? (
              <Button
                variant="contained"
                onClick={handleClose}
                sx={{ textTransform: 'none', fontWeight: 600 }}
              >
                Done
              </Button>
            ) : (
              <Typography variant="caption" sx={{ color: 'text.secondary', fontStyle: 'italic', pr: 1 }}>
                Import in progress... Closing disabled
              </Typography>
            )}
          </>
        )}
      </DialogActions>
    </Dialog>
  );
}

