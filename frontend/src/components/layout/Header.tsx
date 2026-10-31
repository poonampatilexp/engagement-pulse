'use client';

import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Chip,
  Avatar,
  Tooltip,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import NotificationsNoneRoundedIcon from '@mui/icons-material/NotificationsNoneRounded';
import BusinessRoundedIcon from '@mui/icons-material/BusinessRounded';

interface HeaderProps {
  onMobileDrawerToggle: () => void;
}

export default function Header({ onMobileDrawerToggle }: HeaderProps) {
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
            label="Acme Corp"
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
          label="Consultant"
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

        {/* User Profile Pill */}
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
            AC
          </Avatar>
          <Box sx={{ display: { xs: 'none', lg: 'block' }, textAlign: 'left' }}>
            <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
              Alice Consultant
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
              consultant@engagementpulse.com
            </Typography>
          </Box>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

