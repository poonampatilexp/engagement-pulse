'use client';

import React, { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  Drawer,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Button,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material';
import AssessmentRoundedIcon from '@mui/icons-material/AssessmentRounded';
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded';
import EditRoundedIcon from '@mui/icons-material/EditRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import BusinessRoundedIcon from '@mui/icons-material/BusinessRounded';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import { useQuery, useQueries, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/context/AuthContext';
import { apiClient } from '@/lib/api-client';
import { Project, Risk, RiskSeverity, RiskStatus, UpdateRiskPayload } from '@/types/project';

function getSeverityChip(severity: RiskSeverity) {
  switch (severity) {
    case 'critical':
      return <Chip label="CRITICAL" size="small" sx={{ bgcolor: '#FEE2E2', color: '#B91C1C', fontWeight: 700, fontSize: '0.7rem' }} />;
    case 'high':
      return <Chip label="HIGH" size="small" sx={{ bgcolor: '#FFEDD5', color: '#C2410C', fontWeight: 700, fontSize: '0.7rem' }} />;
    case 'medium':
      return <Chip label="MEDIUM" size="small" sx={{ bgcolor: '#FEF3C7', color: '#B45309', fontWeight: 700, fontSize: '0.7rem' }} />;
    default:
      return <Chip label="LOW" size="small" sx={{ bgcolor: '#E0F2FE', color: '#0369A1', fontWeight: 700, fontSize: '0.7rem' }} />;
  }
}

function getStatusChip(status: RiskStatus) {
  switch (status) {
    case 'open':
      return <Chip label="Open" size="small" variant="outlined" color="error" sx={{ fontWeight: 600, fontSize: '0.72rem' }} />;
    case 'mitigating':
      return <Chip label="Mitigating" size="small" variant="outlined" color="warning" sx={{ fontWeight: 600, fontSize: '0.72rem' }} />;
    default:
      return <Chip label="Closed" size="small" variant="outlined" color="success" sx={{ fontWeight: 600, fontSize: '0.72rem' }} />;
  }
}

export default function DashboardPreview() {
  const { user, selectedOrganisation } = useAuth();
  const queryClient = useQueryClient();
  const isConsultant = user?.role === 'consultant';

  const orgId = selectedOrganisation?.id;

  // 1. Fetch projects for the active organisation
  const {
    data: projects = [],
    isLoading: isLoadingProjects,
    error: projectsError,
  } = useQuery({
    queryKey: ['projects', orgId],
    queryFn: () => (orgId ? apiClient.projects.list(orgId) : Promise.resolve([])),
    enabled: !!orgId,
  });

  // 2. Fetch risks for each project concurrently
  const riskQueries = useQueries({
    queries: projects.map((p) => ({
      queryKey: ['risks', p.id],
      queryFn: () => apiClient.risks.list(p.id),
      enabled: !!p.id,
    })),
  });

  const isLoadingRisks = riskQueries.some((q) => q.isLoading);

  // Map project ID to its risk list
  const projectRisksMap = useMemo(() => {
    const map = new Map<number, Risk[]>();
    projects.forEach((project, idx) => {
      const risks = riskQueries[idx]?.data || [];
      map.set(project.id, risks);
    });
    return map;
  }, [projects, riskQueries]);

  // Aggregate metrics
  const totalProjectsCount = projects.length;

  // Non-closed risks (open + mitigating)
  const allOpenRisks = useMemo(() => {
    const all: (Risk & { projectName?: string })[] = [];
    projects.forEach((p) => {
      const risks = projectRisksMap.get(p.id) || [];
      risks
        .filter((r) => r.status !== 'closed')
        .forEach((r) => {
          all.push({ ...r, projectName: p.name });
        });
    });
    return all;
  }, [projects, projectRisksMap]);

  const totalOpenRisksCount = allOpenRisks.length;

  // State for Risk Details Drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTitle, setDrawerTitle] = useState('');
  const [drawerRisks, setDrawerRisks] = useState<(Risk & { projectName?: string })[]>([]);

  // State for Edit Risk Dialog (Consultants only)
  const [editingRisk, setEditingRisk] = useState<Risk | null>(null);
  const [editFormData, setEditFormData] = useState<UpdateRiskPayload>({});
  const [editError, setEditError] = useState<string | null>(null);

  // Mutation to update risk
  const updateRiskMutation = useMutation({
    mutationFn: ({ riskId, data }: { riskId: number; data: UpdateRiskPayload }) =>
      apiClient.risks.update(riskId, data),
    onSuccess: (updatedRisk) => {
      // Invalidate relevant queries so risk score and risk list recalculate
      queryClient.invalidateQueries({ queryKey: ['risks', updatedRisk.project] });
      queryClient.invalidateQueries({ queryKey: ['projects', orgId] });
      setEditingRisk(null);
      setEditError(null);
    },
    onError: (err: any) => {
      setEditError(err.message || 'Failed to update risk.');
    },
  });

  // Handle clicking "Open Risks" summary card -> show all non-closed risks for active organisation
  const handleOpenAllRisks = () => {
    setDrawerTitle(`Open Risks — ${selectedOrganisation?.name || 'Active Organisation'}`);
    setDrawerRisks(allOpenRisks);
    setDrawerOpen(true);
  };

  // Handle clicking a specific project's Open Risks Count -> show that project's non-closed risks
  const handleOpenProjectRisks = (project: Project) => {
    const risks = (projectRisksMap.get(project.id) || [])
      .filter((r) => r.status !== 'closed')
      .map((r) => ({ ...r, projectName: project.name }));
    setDrawerTitle(`Open Risks — ${project.name}`);
    setDrawerRisks(risks);
    setDrawerOpen(true);
  };

  // Open Edit Dialog for Consultant
  const handleStartEdit = (risk: Risk) => {
    setEditingRisk(risk);
    setEditFormData({
      title: risk.title,
      description: risk.description,
      severity: risk.severity,
      status: risk.status,
      owner: risk.owner,
    });
    setEditError(null);
  };

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRisk) return;
    updateRiskMutation.mutate({ riskId: editingRisk.id, data: editFormData });
  };

  // Keep drawer risks updated when queries change
  React.useEffect(() => {
    if (drawerOpen) {
      // If drawer title contains project name, find that project
      const matchedProject = projects.find((p) => drawerTitle.includes(p.name));
      if (matchedProject) {
        const risks = (projectRisksMap.get(matchedProject.id) || [])
          .filter((r) => r.status !== 'closed')
          .map((r) => ({ ...r, projectName: matchedProject.name }));
        setDrawerRisks(risks);
      } else {
        setDrawerRisks(allOpenRisks);
      }
    }
  }, [allOpenRisks, projectRisksMap, drawerOpen, projects, drawerTitle]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3.5 }}>
      {/* Active Tenant Context Bar */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, color: '#0F172A' }}>
            {selectedOrganisation?.name || 'Organisation'} Overview
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
            Active engagement risk status and project metrics
          </Typography>
        </Box>
      </Box>

      {/* 1. Only Two Summary Cards: Total Projects & Open Risks */}
      <Grid container spacing={3}>
        {/* Card 1: Total Projects */}
        <Grid item xs={12} sm={6}>
          <Card
            sx={{
              borderRadius: 3,
              border: '1px solid #E2E8F0',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              transition: 'box-shadow 0.2s',
              '&:hover': { boxShadow: '0 4px 12px rgba(0,0,0,0.06)' },
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Box>
                  <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Total Projects
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: '#0F172A', mt: 1 }}>
                    {isLoadingProjects ? <CircularProgress size={28} sx={{ color: 'primary.main' }} /> : totalProjectsCount}
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary', mt: 1 }}>
                    Active projects in {selectedOrganisation?.name || 'organisation'}
                  </Typography>
                </Box>
                <Box
                  sx={{
                    width: 44,
                    height: 44,
                    borderRadius: 2.5,
                    bgcolor: '#FFF3EE',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'primary.main',
                  }}
                >
                  <AssessmentRoundedIcon />
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Card 2: Open Risks (Clickable to view non-closed risks) */}
        <Grid item xs={12} sm={6}>
          <Card
            onClick={handleOpenAllRisks}
            data-testid="open-risks-card"
            sx={{
              borderRadius: 3,
              border: '1px solid #E2E8F0',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              cursor: 'pointer',
              transition: 'all 0.2s',
              '&:hover': {
                boxShadow: '0 4px 14px rgba(233,76,23,0.12)',
                borderColor: 'primary.light',
                bgcolor: '#FFFAF8',
              },
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Box>
                  <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Open Risks
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: totalOpenRisksCount > 0 ? '#E94C17' : '#0F172A', mt: 1 }}>
                    {isLoadingRisks ? <CircularProgress size={28} sx={{ color: 'primary.main' }} /> : totalOpenRisksCount}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
                    <Typography variant="body2" sx={{ color: 'primary.main', fontWeight: 600 }}>
                      Open & mitigating risks • Click to view
                    </Typography>
                    <ArrowForwardRoundedIcon sx={{ fontSize: 16, color: 'primary.main' }} />
                  </Box>
                </Box>
                <Box
                  sx={{
                    width: 44,
                    height: 44,
                    borderRadius: 2.5,
                    bgcolor: '#FEF3C7',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#D97706',
                  }}
                >
                  <WarningAmberRoundedIcon />
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 2. One Projects Table: Project Name, Risk Score, Open Risks Count */}
      <Card
        sx={{
          borderRadius: 3,
          border: '1px solid #E2E8F0',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          overflow: 'hidden',
        }}
      >
        <Box sx={{ p: 2.5, borderBottom: '1px solid #E2E8F0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#0F172A' }}>
            Projects
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {projects.length} {projects.length === 1 ? 'project' : 'projects'} tracked
          </Typography>
        </Box>

        {isLoadingProjects ? (
          <Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress size={32} sx={{ color: 'primary.main' }} />
          </Box>
        ) : projectsError ? (
          <Alert severity="error" sx={{ m: 2.5 }}>
            Failed to load projects for this organisation.
          </Alert>
        ) : projects.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="body1" sx={{ color: 'text.secondary' }}>
              No projects found for this organisation.
            </Typography>
          </Box>
        ) : (
          <TableContainer component={Paper} elevation={0}>
            <Table sx={{ minWidth: 500 }}>
              <TableHead sx={{ backgroundColor: '#F8FAFC' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700, color: '#475569', fontSize: '0.8rem', textTransform: 'uppercase' }}>
                    Project Name
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700, color: '#475569', fontSize: '0.8rem', textTransform: 'uppercase' }}>
                    Risk Score
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700, color: '#475569', fontSize: '0.8rem', textTransform: 'uppercase' }}>
                    Open Risks Count
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {projects.map((project) => {
                  const risks = projectRisksMap.get(project.id) || [];
                  const openCount = risks.filter((r) => r.status !== 'closed').length;

                  return (
                    <TableRow
                      key={project.id}
                      hover
                      sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                    >
                      {/* Column 1: Project Name */}
                      <TableCell sx={{ py: 2 }}>
                        <Typography variant="body1" sx={{ fontWeight: 600, color: '#0F172A' }}>
                          {project.name}
                        </Typography>
                      </TableCell>

                      {/* Column 2: Risk Score */}
                      <TableCell sx={{ py: 2 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Chip
                            label={`${project.risk_score} / 100`}
                            size="small"
                            sx={{
                              fontWeight: 700,
                              bgcolor: project.risk_score > 50 ? '#FEE2E2' : project.risk_score > 20 ? '#FFEDD5' : '#ECFDF5',
                              color: project.risk_score > 50 ? '#B91C1C' : project.risk_score > 20 ? '#C2410C' : '#047857',
                            }}
                          />
                        </Box>
                      </TableCell>

                      {/* Column 3: Open Risks Count (Clickable!) */}
                      <TableCell sx={{ py: 2 }}>
                        <Chip
                          label={`${openCount} open ${openCount === 1 ? 'risk' : 'risks'}`}
                          size="small"
                          clickable
                          onClick={() => handleOpenProjectRisks(project)}
                          data-testid={`project-open-risks-${project.id}`}
                          sx={{
                            fontWeight: 600,
                            bgcolor: openCount > 0 ? '#FFF3EE' : '#F1F5F9',
                            color: openCount > 0 ? 'primary.main' : '#64748B',
                            border: '1px solid',
                            borderColor: openCount > 0 ? '#FECBB8' : '#CBD5E1',
                            '&:hover': {
                              bgcolor: '#FEE5DC',
                              borderColor: 'primary.main',
                            },
                          }}
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>

      {/* 3. Risk Details Drawer (Shows non-closed risks) */}
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{
          sx: {
            width: { xs: '100%', sm: 540 },
            p: 3,
            backgroundColor: '#F8FAFC',
          },
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#0F172A' }}>
            {drawerTitle}
          </Typography>
          <IconButton onClick={() => setDrawerOpen(false)} size="small" aria-label="close drawer">
            <CloseRoundedIcon />
          </IconButton>
        </Box>

        <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
          {isConsultant ? 'Review and manage non-closed project risks.' : 'Read-only view of non-closed engagement risks.'}
        </Typography>

        <Divider sx={{ mb: 2.5 }} />

        {drawerRisks.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center', bgcolor: '#FFFFFF', borderRadius: 2, border: '1px solid #E2E8F0' }}>
            <Typography variant="body1" sx={{ color: 'text.secondary', fontWeight: 500 }}>
              No open or mitigating risks.
            </Typography>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {drawerRisks.map((risk) => (
              <Card
                key={risk.id}
                sx={{
                  borderRadius: 2.5,
                  border: '1px solid #E2E8F0',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                }}
              >
                <CardContent sx={{ p: 2.5 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1 }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="h6" sx={{ fontWeight: 700, color: '#0F172A', fontSize: '1rem' }}>
                        {risk.title}
                      </Typography>
                      {risk.projectName && (
                        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 0.25 }}>
                          Project: <strong>{risk.projectName}</strong>
                        </Typography>
                      )}
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getSeverityChip(risk.severity)}
                      {getStatusChip(risk.status)}
                    </Box>
                  </Box>

                  <Typography variant="body2" sx={{ color: '#334155', mt: 1.5, lineHeight: 1.5 }}>
                    {risk.description || 'No description provided.'}
                  </Typography>

                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2, pt: 1.5, borderTop: '1px solid #F1F5F9' }}>
                    <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 500 }}>
                      Owner: <strong>{risk.owner || 'Unassigned'}</strong>
                    </Typography>

                    {/* Consultants can edit; Client viewers are read-only */}
                    {isConsultant && (
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<EditRoundedIcon fontSize="small" />}
                        onClick={() => handleStartEdit(risk)}
                        sx={{ fontSize: '0.75rem', py: 0.5, px: 1.25 }}
                      >
                        Edit
                      </Button>
                    )}
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}
      </Drawer>

      {/* 4. Edit Risk Dialog (Consultant only) */}
      <Dialog
        open={Boolean(editingRisk)}
        onClose={() => setEditingRisk(null)}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle sx={{ fontWeight: 700, pb: 1 }}>
          Edit Risk Details
        </DialogTitle>
        <Box component="form" onSubmit={handleSaveEdit}>
          <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
            {editError && (
              <Alert severity="error" sx={{ mb: 1 }}>
                {editError}
              </Alert>
            )}

            <TextField
              label="Title"
              fullWidth
              required
              value={editFormData.title || ''}
              onChange={(e) => setEditFormData({ ...editFormData, title: e.target.value })}
            />

            <TextField
              label="Description"
              fullWidth
              multiline
              rows={3}
              value={editFormData.description || ''}
              onChange={(e) => setEditFormData({ ...editFormData, description: e.target.value })}
            />

            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  select
                  label="Severity"
                  fullWidth
                  value={editFormData.severity || 'medium'}
                  onChange={(e) => setEditFormData({ ...editFormData, severity: e.target.value as RiskSeverity })}
                >
                  <MenuItem value="low">Low (Weight 1)</MenuItem>
                  <MenuItem value="medium">Medium (Weight 2)</MenuItem>
                  <MenuItem value="high">High (Weight 3)</MenuItem>
                  <MenuItem value="critical">Critical (Weight 4)</MenuItem>
                </TextField>
              </Grid>

              <Grid item xs={6}>
                <TextField
                  select
                  label="Status"
                  fullWidth
                  value={editFormData.status || 'open'}
                  onChange={(e) => setEditFormData({ ...editFormData, status: e.target.value as RiskStatus })}
                >
                  <MenuItem value="open">Open (Weight 3)</MenuItem>
                  <MenuItem value="mitigating">Mitigating (Weight 2)</MenuItem>
                  <MenuItem value="closed">Closed (Weight 0)</MenuItem>
                </TextField>
              </Grid>
            </Grid>

            <TextField
              label="Owner"
              fullWidth
              value={editFormData.owner || ''}
              onChange={(e) => setEditFormData({ ...editFormData, owner: e.target.value })}
            />
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2.5 }}>
            <Button onClick={() => setEditingRisk(null)} disabled={updateRiskMutation.isPending}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={updateRiskMutation.isPending}
              sx={{ fontWeight: 600 }}
            >
              {updateRiskMutation.isPending ? <CircularProgress size={20} sx={{ color: '#FFFFFF' }} /> : 'Save Changes'}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Box>
  );
}
