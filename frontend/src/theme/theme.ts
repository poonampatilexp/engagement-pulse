'use client';

import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#E94C17', // Engagement Pulse Brand Reddish-Orange
      light: '#FF6F42',
      dark: '#C23809',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#0D9488', // Emerald / Teal
      light: '#2DD4BF',
      dark: '#0F766E',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#F8FAFC', // Slate 50
      paper: '#FFFFFF',
    },
    text: {
      primary: '#0F172A', // Slate 900
      secondary: '#64748B', // Slate 500
      disabled: '#94A3B8', // Slate 400
    },
    divider: '#E2E8F0', // Slate 200
    success: {
      main: '#10B981', // Emerald 500
      light: '#D1FAE5',
      dark: '#047857',
    },
    warning: {
      main: '#F59E0B', // Amber 500
      light: '#FEF3C7',
      dark: '#B45309',
    },
    error: {
      main: '#EF4444', // Red 500
      light: '#FEE2E2',
      dark: '#B91C1C',
    },
    info: {
      main: '#0EA5E9', // Sky 500
      light: '#E0F2FE',
      dark: '#0369A1',
    },
  },
  typography: {
    fontFamily: [
      'Inter',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: {
      fontSize: '2rem',
      fontWeight: 700,
      letterSpacing: '-0.025em',
      color: '#0F172A',
    },
    h2: {
      fontSize: '1.5rem',
      fontWeight: 700,
      letterSpacing: '-0.02em',
      color: '#0F172A',
    },
    h3: {
      fontSize: '1.25rem',
      fontWeight: 600,
      letterSpacing: '-0.015em',
      color: '#0F172A',
    },
    h4: {
      fontSize: '1.125rem',
      fontWeight: 600,
      color: '#0F172A',
    },
    h5: {
      fontSize: '1rem',
      fontWeight: 600,
      color: '#0F172A',
    },
    h6: {
      fontSize: '0.875rem',
      fontWeight: 600,
      color: '#0F172A',
    },
    body1: {
      fontSize: '0.9375rem',
      lineHeight: 1.6,
      color: '#334155',
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.5,
      color: '#64748B',
    },
    button: {
      textTransform: 'none',
      fontWeight: 600,
      fontSize: '0.875rem',
    },
    caption: {
      fontSize: '0.75rem',
      color: '#64748B',
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 16px',
          fontWeight: 600,
          transition: 'all 0.15s ease-in-out',
        },
        containedPrimary: {
          boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
          '&:hover': {
            boxShadow: '0 4px 6px -1px rgba(233, 76, 23, 0.25), 0 2px 4px -2px rgba(233, 76, 23, 0.25)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          border: '1px solid #E2E8F0',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.03), 0 1px 2px -1px rgba(0, 0, 0, 0.03)',
          transition: 'box-shadow 0.2s ease-in-out, border-color 0.2s ease-in-out',
          '&:hover': {
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
        rounded: {
          borderRadius: 12,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#FFFFFF',
          color: '#0F172A',
          borderBottom: '1px solid #E2E8F0',
          boxShadow: 'none',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#FFFFFF',
          borderRight: '1px solid #E2E8F0',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          fontWeight: 600,
          fontSize: '0.75rem',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid #F1F5F9',
          padding: '12px 16px',
        },
        head: {
          fontWeight: 600,
          color: '#475569',
          backgroundColor: '#F8FAFC',
          fontSize: '0.75rem',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        },
      },
    },
  },
});

