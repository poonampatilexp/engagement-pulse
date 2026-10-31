'use client';

import React from 'react';
import Link from 'next/link';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Chip,
  Avatar,
  Tooltip,
  Button,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import NotificationsNoneRoundedIcon from '@mui/icons-material/NotificationsNoneRounded';
import BusinessRoundedIcon from '@mui/icons-material/BusinessRounded';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import LoginRoundedIcon from '@mui/icons-material/LoginRounded';
import { useAuth } from '@/context/AuthContext';

interface HeaderProps {
  onMobileDrawerToggle: () => void;
}

export default function Header({ onMobileDrawerToggle }: HeaderProps) {
  const { user, isAuthenticated, logout } = useAuth();

  const activeOrgName = user
    ? user.role === 'client_viewer'
      ? user.organisation?.name || 'Assigned Organisation'
      : user.organisations?.[0]?.name || 'All Assigned Organisations'
    : 'Acme Corp';

  const userInitials = user?.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'AC';

  return (
    <AppBar position="sticky">
      <Toolbar sx={{ height: 64, px: { xs: 2, sm: 3 }, gap: 2 }}>
        {/* Mobile menu button */}
        <IconButton
          edge="start"
          color="inherit"
          aria-label="open drawer"
          onClick={onMobileDrawerToggle}
          sx={{ display: { md: 'none' } }}
        >
          <MenuIcon />
        </IconButton>

        {/* Current Context / Breadcrumb Title */}
        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
          <Typography variant="h4" sx={{ fontWeight: 700, fontSize: { xs: '1rem', sm: '1.2rem' } }}>
            Overview Dashboard
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary', display: { xs: 'none', sm: 'block' } }}>
            Real-time engagement risk tracking
          </Typography>
        </Box>

        <Box sx={{ flexGrow: 1 }} />

        {/* Organisation Context Selector Chip */}
        <Tooltip title="Current active tenant organisation" arrow>
          <Chip
            icon={<BusinessRoundedIcon fontSize="small" />}
            label={activeOrgName}
            variant="outlined"
            size="medium"
            sx={{
              fontWeight: 600,
              borderColor: '#CBD5E1',
              backgroundColor: '#F8FAFC',
              display: { xs: 'none', sm: 'inline-flex' },
            }}
          />
        </Tooltip>

        {/* User Role Badge */}
        <Chip
          label={user ? (user.role === 'consultant' ? 'Consultant' : 'Client Viewer') : 'Consultant'}
          size="small"
          color="primary"
          sx={{
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            fontSize: '0.7rem',
          }}
        />

        {/* Notifications (Not yet implemented) */}
        <Tooltip title="Real-time notifications will be active in the WebSocket milestone" arrow>
          <span>
            <IconButton
              size="small"
              disabled
              sx={{
                border: '1px solid #E2E8F0',
                borderRadius: 2,
                p: 0.75,
                color: '#94A3B8',
              }}
            >
              <NotificationsNoneRoundedIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>

        {/* User Profile / Auth State */}
        {isAuthenticated && user ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Avatar
                sx={{
                  width: 34,
                  height: 34,
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  backgroundColor: 'primary.main',
                }}
              >
                {userInitials}
              </Avatar>
              <Box sx={{ display: { xs: 'none', lg: 'block' }, textAlign: 'left' }}>
                <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
                  {user.name}
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
                  {user.email}
                </Typography>
              </Box>
            </Box>

            <Tooltip title="Sign Out" arrow>
              <IconButton
                size="small"
                onClick={logout}
                component={Link}
                href="/login"
                sx={{
                  border: '1px solid #E2E8F0',
                  borderRadius: 2,
                  p: 0.75,
                  '&:hover': { bgcolor: '#FEE2E2', color: '#EF4444' },
                }}
              >
                <LogoutRoundedIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        ) : (
          <Button
            component={Link}
            href="/login"
            variant="contained"
            size="small"
            startIcon={<LoginRoundedIcon fontSize="small" />}
            sx={{ fontWeight: 600 }}
          >
            Sign In
          </Button>
        )}
      </Toolbar>
    </AppBar>
  );
}

