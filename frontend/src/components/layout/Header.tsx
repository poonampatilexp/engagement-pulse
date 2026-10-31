'use client';

import React, { useState } from 'react';
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
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import NotificationsNoneRoundedIcon from '@mui/icons-material/NotificationsNoneRounded';
import BusinessRoundedIcon from '@mui/icons-material/BusinessRounded';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import LoginRoundedIcon from '@mui/icons-material/LoginRounded';
import ArrowDropDownRoundedIcon from '@mui/icons-material/ArrowDropDownRounded';
import CheckRoundedIcon from '@mui/icons-material/CheckRounded';
import { useAuth } from '@/context/AuthContext';
import { OrganisationRef } from '@/types/auth';

interface HeaderProps {
  onMobileDrawerToggle: () => void;
}

export default function Header({ onMobileDrawerToggle }: HeaderProps) {
  const { user, isAuthenticated, logout, selectedOrganisation, setSelectedOrganisation, availableOrganisations } = useAuth();
  const [orgAnchorEl, setOrgAnchorEl] = useState<null | HTMLElement>(null);

  const activeOrgName = selectedOrganisation?.name || (user?.role === 'client_viewer' ? user.organisation?.name : user?.organisations?.[0]?.name) || 'Acme Corp';

  const userInitials = user?.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'AC';

  const isConsultant = user?.role === 'consultant';
  const canSwitchOrgs = isConsultant && availableOrganisations.length > 1;

  const handleOrgClick = (event: React.MouseEvent<HTMLElement>) => {
    if (canSwitchOrgs) {
      setOrgAnchorEl(event.currentTarget);
    }
  };

  const handleOrgSelect = (org: OrganisationRef) => {
    setSelectedOrganisation(org);
    setOrgAnchorEl(null);
  };

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
        <Tooltip title={canSwitchOrgs ? "Click to switch active tenant organisation" : "Current active tenant organisation"} arrow>
          <Chip
            icon={<BusinessRoundedIcon fontSize="small" />}
            label={activeOrgName}
            onClick={canSwitchOrgs ? handleOrgClick : undefined}
            onDelete={canSwitchOrgs ? handleOrgClick : undefined}
            deleteIcon={canSwitchOrgs ? <ArrowDropDownRoundedIcon /> : undefined}
            variant="outlined"
            size="medium"
            data-testid="organisation-selector-chip"
            sx={{
              fontWeight: 600,
              borderColor: '#CBD5E1',
              backgroundColor: '#F8FAFC',
              cursor: canSwitchOrgs ? 'pointer' : 'default',
              display: { xs: 'none', sm: 'inline-flex' },
              '&:hover': canSwitchOrgs ? { bgcolor: '#FFF7ED', borderColor: 'primary.main' } : {},
            }}
          />
        </Tooltip>

        {/* Organisation Switching Menu (Consultants with multiple organisations only) */}
        {canSwitchOrgs && (
          <Menu
            anchorEl={orgAnchorEl}
            open={Boolean(orgAnchorEl)}
            onClose={() => setOrgAnchorEl(null)}
            PaperProps={{
              sx: {
                mt: 1,
                minWidth: 200,
                borderRadius: 2,
                boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
              },
            }}
          >
            <Box sx={{ px: 2, py: 1, borderBottom: '1px solid #E2E8F0' }}>
              <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', textTransform: 'uppercase' }}>
                Switch Organisation
              </Typography>
            </Box>
            {availableOrganisations.map((org) => {
              const isSelected = selectedOrganisation?.id === org.id;
              return (
                <MenuItem
                  key={org.id}
                  onClick={() => handleOrgSelect(org)}
                  selected={isSelected}
                  sx={{ py: 1 }}
                >
                  <ListItemIcon sx={{ minWidth: 28 }}>
                    {isSelected ? <CheckRoundedIcon fontSize="small" color="primary" /> : <BusinessRoundedIcon fontSize="small" sx={{ color: '#94A3B8' }} />}
                  </ListItemIcon>
                  <ListItemText primary={org.name} primaryTypographyProps={{ fontWeight: isSelected ? 700 : 500, fontSize: '0.875rem' }} />
                </MenuItem>
              );
            })}
          </Menu>
        )}

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
                aria-label="sign out"
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
