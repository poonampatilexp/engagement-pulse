'use client';

import React from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import UploadFileRoundedIcon from '@mui/icons-material/UploadFileRounded';
import AssessmentRoundedIcon from '@mui/icons-material/AssessmentRounded';
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded';
import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded';
import SpeedRoundedIcon from '@mui/icons-material/SpeedRounded';
import MoreVertRoundedIcon from '@mui/icons-material/MoreVertRounded';

interface StatItem {
  title: string;
  value: string;
  unit?: string;
  subtitle: string;
  icon: React.ReactNode;
  iconBg: string;
}

const STAT_CARDS: StatItem[] = [
  {
    title: 'Active Projects',
    value: '2',
    subtitle: '2 active in Acme Corp',
    icon: <AssessmentRoundedIcon fontSize="small" sx={{ color: '#E94C17' }} />,
    iconBg: '#FFF3EE',
  },
  {
    title: 'Identified Risks',
    value: '4',
    subtitle: '1 open • 2 mitigating',
    icon: <WarningAmberRoundedIcon fontSize="small" sx={{ color: '#D97706' }} />,
    iconBg: '#FEF3C7',
  },
  {
    title: 'Project Risk Score',
    value: '13',
    unit: '/ 100',
    subtitle: 'Peak: ERP Modernisation',
    icon: <SpeedRoundedIcon fontSize="small" sx={{ color: '#EA580C' }} />,
    iconBg: '#FFEDD5',
  },
  {
    title: 'Resolved Risks',
    value: '1',
    subtitle: '1 risk mitigated & closed',
    icon: <CheckCircleOutlineRoundedIcon fontSize="small" sx={{ color: '#059669' }} />,
    iconBg: '#D1FAE5',
  },
];

const RECENT_PROJECTS = [
  {
    id: 1,
    name: 'ERP Modernisation',
    risksCount: 2,
    score: 13,
    status: 'In Progress',
    updated: '10 mins ago',
  },
  {
    id: 2,
    name: 'Acme Core Platform',
    risksCount: 2,
    score: 4,
    status: 'Healthy',
    updated: '1 hour ago',
  },
];

const RECENT_RISKS = [
  {
    id: 101,
    project: 'ERP Modernisation',
    title: 'Legacy Database Migration Delay',
    severity: 'high',
    status: 'open',
    contribution: 9, // 3 x 3
    owner: 'Data Engineering Lead',
  },
  {
    id: 102,
    project: 'ERP Modernisation',
    title: 'Third-party API Rate Limiting',
    severity: 'medium',
    status: 'mitigating',
    contribution: 4, // 2 x 2
    owner: 'Integration Team',
  },
  {
    id: 103,
    project: 'Acme Core Platform',
    title: 'CI/CD Deployment Bottlenecks',
    severity: 'medium',
    status: 'mitigating',
    contribution: 4, // 2 x 2
    owner: 'DevOps Lead',
  },
  {
    id: 104,
    project: 'Acme Core Platform',
    title: 'SSL Certificate Auto-Renewal',
    severity: 'low',
    status: 'closed',
    contribution: 0, // 1 x 0
    owner: 'Security Specialist',
  },
];

function getSeverityChip(severity: string) {
  switch (severity) {
    case 'critical':
      return <Chip label="CRITICAL" size="small" sx={{ bgcolor: '#FEE2E2', color: '#B91C1C', fontWeight: 700 }} />;
    case 'high':
      return <Chip label="HIGH" size="small" sx={{ bgcolor: '#FFEDD5', color: '#C2410C', fontWeight: 700 }} />;
    case 'medium':
      return <Chip label="MEDIUM" size="small" sx={{ bgcolor: '#FEF3C7', color: '#B45309', fontWeight: 700 }} />;
    default:
      return <Chip label="LOW" size="small" sx={{ bgcolor: '#E0F2FE', color: '#0369A1', fontWeight: 700 }} />;
  }
}

function getStatusChip(status: string) {
  switch (status) {
    case 'open':
      return <Chip label="Open" size="small" variant="outlined" color="error" sx={{ fontWeight: 600 }} />;
    case 'mitigating':
      return <Chip label="Mitigating" size="small" variant="outlined" color="warning" sx={{ fontWeight: 600 }} />;
    default:
      return <Chip label="Closed" size="small" variant="outlined" color="success" sx={{ fontWeight: 600 }} />;
  }
}

export default function DashboardPreview() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3.5 }}>
      {/* Hero Welcome & Action Bar */}
      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          justifyContent: 'space-between',
          alignItems: { xs: 'flex-start', sm: 'center' },
          gap: 2,
        }}
      >
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.5 }}>
            <Typography variant="h2" sx={{ fontSize: { xs: '1.4rem', sm: '1.75rem' }, fontWeight: 700 }}>
              Acme Corp
            </Typography>
            <Chip
              label="Demo Preview"
              size="small"
              variant="outlined"
              sx={{
                bgcolor: '#F8FAFC',
                color: '#64748B',
                fontWeight: 600,
                border: '1px solid #CBD5E1',
              }}
            />
          </Box>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            Multi-tenant project risk evaluation with automatic backend score calculation.
          </Typography>
        </Box>

        {/* Action Buttons (Disabled with upcoming tooltips) */}
        <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
          <Tooltip title="Asynchronous CSV import via Dramatiq & Redis will be active in Prompt 4" arrow>
            <span>
              <Button
                variant="outlined"
                startIcon={<UploadFileRoundedIcon />}
                disabled
                sx={{
                  borderColor: '#E2E8F0 !important',
                  color: '#94A3B8 !important',
                }}
              >
                Import CSV (Upcoming)
              </Button>
            </span>
          </Tooltip>

          <Tooltip title="Project creation modal form will be wired in the project workflow prompt" arrow>
            <span>
              <Button
                variant="contained"
                startIcon={<AddRoundedIcon />}
                disabled
                sx={{
                  bgcolor: '#E2E8F0 !important',
                  color: '#94A3B8 !important',
                }}
              >
                New Project (Upcoming)
              </Button>
            </span>
          </Tooltip>
        </Box>
      </Box>

      {/* Summary KPI Metric Cards (Strictly Equal Height & Baseline Aligned) */}
      <Grid container spacing={2.5} alignItems="stretch">
        {STAT_CARDS.map((stat, i) => (
          <Grid item xs={12} sm={6} lg={3} key={i} sx={{ display: 'flex' }}>
            <Card
              sx={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                borderRadius: 3,
                border: '1px solid #E2E8F0',
                boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
                height: '100%',
              }}
            >
              <CardContent
                sx={{
                  p: 2.5,
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  '&:last-child': { pb: 2.5 },
                }}
              >
                {/* Top Row: Label & Icon */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                  <Typography
                    variant="caption"
                    sx={{
                      fontWeight: 700,
                      color: '#64748B',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      fontSize: '0.72rem',
                    }}
                  >
                    {stat.title}
                  </Typography>
                  <Box
                    sx={{
                      width: 36,
                      height: 36,
                      borderRadius: 2,
                      backgroundColor: stat.iconBg,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {stat.icon}
                  </Box>
                </Box>

                {/* Middle Row: Stat Value */}
                <Box sx={{ my: 1, display: 'flex', alignItems: 'baseline', gap: 0.5 }}>
                  <Typography
                    variant="h2"
                    sx={{
                      fontSize: '1.875rem',
                      fontWeight: 700,
                      color: '#0F172A',
                      lineHeight: 1,
                    }}
                  >
                    {stat.value}
                  </Typography>
                  {stat.unit && (
                    <Typography
                      variant="body2"
                      sx={{
                        color: '#64748B',
                        fontWeight: 600,
                      }}
                    >
                      {stat.unit}
                    </Typography>
                  )}
                </Box>

                {/* Bottom Row: Concise Context (Never Truncates) */}
                <Typography
                  variant="caption"
                  sx={{
                    color: '#64748B',
                    fontWeight: 500,
                    display: 'block',
                    mt: 0.5,
                  }}
                >
                  {stat.subtitle}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Main Grid: Projects & Recent Risks (Equal Stretch) */}
      <Grid container spacing={3} alignItems="stretch">
        {/* Projects Overview */}
        <Grid item xs={12} lg={5} sx={{ display: 'flex' }}>
          <Card
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              borderRadius: 3,
              border: '1px solid #E2E8F0',
            }}
          >
            <CardContent sx={{ p: 3, flex: 1, display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h3">Organisation Projects</Typography>
                <Button size="small" variant="text" disabled sx={{ color: '#94A3B8 !important' }}>
                  View All
                </Button>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
                {RECENT_PROJECTS.map((proj) => (
                  <Box
                    key={proj.id}
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      border: '1px solid #E2E8F0',
                      backgroundColor: '#FFFFFF',
                      transition: 'border-color 0.2s',
                      '&:hover': { borderColor: 'primary.light' },
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                      <Box>
                        <Typography variant="h4" sx={{ fontSize: '1rem' }}>
                          {proj.name}
                        </Typography>
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          {proj.risksCount} active risks • Updated {proj.updated}
                        </Typography>
                      </Box>
                      <Chip
                        label={`Score: ${proj.score}`}
                        size="small"
                        sx={{
                          fontWeight: 700,
                          bgcolor: proj.score > 20 ? '#FEE2E2' : proj.score > 0 ? '#FEF3C7' : '#D1FAE5',
                          color: proj.score > 20 ? '#B91C1C' : proj.score > 0 ? '#B45309' : '#047857',
                        }}
                      />
                    </Box>

                    <Box sx={{ mt: 1.5 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          Risk Exposure Gauge
                        </Typography>
                        <Typography variant="caption" sx={{ fontWeight: 600 }}>
                          {proj.score}%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={Math.min(proj.score, 100)}
                        sx={{
                          height: 6,
                          borderRadius: 3,
                          backgroundColor: '#F1F5F9',
                          '& .MuiLinearProgress-bar': {
                            backgroundColor: proj.score > 20 ? '#EF4444' : proj.score > 0 ? '#F59E0B' : '#10B981',
                          },
                        }}
                      />
                    </Box>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Identified Risks Table */}
        <Grid item xs={12} lg={7} sx={{ display: 'flex' }}>
          <Card
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              borderRadius: 3,
              border: '1px solid #E2E8F0',
            }}
          >
            <CardContent sx={{ p: 3, flex: 1, display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h3">Active Risk Register</Typography>
                <Button size="small" variant="text" disabled sx={{ color: '#94A3B8 !important' }}>
                  Filter Risks
                </Button>
              </Box>

              <TableContainer sx={{ border: '1px solid #F1F5F9', borderRadius: 2, flex: 1 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Risk Title</TableCell>
                      <TableCell>Severity</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell align="center">Impact</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {RECENT_RISKS.map((risk) => (
                      <TableRow key={risk.id} hover>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 600, color: '#0F172A' }}>
                            {risk.title}
                          </Typography>
                          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                            {risk.owner} • {risk.project}
                          </Typography>
                        </TableCell>
                        <TableCell>{getSeverityChip(risk.severity)}</TableCell>
                        <TableCell>{getStatusChip(risk.status)}</TableCell>
                        <TableCell align="center">
                          <Typography variant="body2" sx={{ fontWeight: 700, color: '#1E293B' }}>
                            +{risk.contribution}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="Actions will be available in the Risk Management milestone" arrow>
                            <span>
                              <IconButton size="small" disabled sx={{ color: '#94A3B8 !important' }}>
                                <MoreVertRoundedIcon fontSize="small" />
                              </IconButton>
                            </span>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
