'use client';

import React from 'react';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  IconButton,
  Divider,
  Tooltip,
  Chip,
} from '@mui/material';
import DashboardRoundedIcon from '@mui/icons-material/DashboardRounded';
import AssignmentRoundedIcon from '@mui/icons-material/AssignmentRounded';
import ShieldRoundedIcon from '@mui/icons-material/ShieldRounded';
import BusinessRoundedIcon from '@mui/icons-material/BusinessRounded';
import ChevronLeftRoundedIcon from '@mui/icons-material/ChevronLeftRounded';
import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded';
import { useAuth } from '@/context/AuthContext';
import PulseIcon from '@mui/icons-material/TimelineRounded';

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

const NAV_ITEMS = [
  { label: 'Dashboard', icon: <DashboardRoundedIcon />, href: '/', active: true },
  { label: 'Projects', icon: <AssignmentRoundedIcon />, href: '/projects', badge: '2' },
  { label: 'Risks', icon: <ShieldRoundedIcon />, href: '/risks', badge: '5' },
  { label: 'Organisations', icon: <BusinessRoundedIcon />, href: '/organisations' },
];

export const DRAWER_WIDTH = 260;
export const COLLAPSED_WIDTH = 76;

export default function Sidebar({
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onMobileClose,
}: SidebarProps) {
  const { selectedOrganisation } = useAuth();
  const orgName = selectedOrganisation?.name || 'Assigned Organisation';

  const drawerContent = (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#FFFFFF',
      }}
    >
      {/* Brand Header */}
      <Box
        sx={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          px: collapsed ? 2 : 2.5,
          justifyContent: collapsed ? 'center' : 'space-between',
          borderBottom: '1px solid #E2E8F0',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 38,
              height: 38,
              borderRadius: 2,
              backgroundColor: 'primary.main',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFFFFF',
              boxShadow: '0 2px 4px rgba(233, 76, 23, 0.25)',
            }}
          >
            <PulseIcon />
          </Box>
          {!collapsed && (
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
                Engagement
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  color: 'primary.main',
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                }}
              >
                Pulse
              </Typography>
            </Box>
          )}
        </Box>
      </Box>

      {/* Tenant Context Pill */}
      {!collapsed && (
        <Box sx={{ px: 2, pt: 2, pb: 1 }}>
          <Box
            sx={{
              p: 1.5,
              borderRadius: 2,
              backgroundColor: '#F1F5F9',
              border: '1px solid #E2E8F0',
            }}
          >
            <Typography variant="caption" sx={{ color: '#64748B', display: 'block', fontWeight: 600 }}>
              ACTIVE ORGANISATION
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 700, color: '#0F172A', mt: 0.25 }}>
              {orgName}
            </Typography>
          </Box>
        </Box>
      )}

      {/* Navigation List */}
      <List sx={{ px: 1.5, py: 1.5, flex: 1 }}>
        {NAV_ITEMS.map((item) => {
          const button = (
            <ListItemButton
              key={item.label}
              selected={item.active}
              sx={{
                borderRadius: 2,
                mb: 0.5,
                px: collapsed ? 1.5 : 2,
                py: 1.25,
                justifyContent: collapsed ? 'center' : 'flex-start',
                backgroundColor: item.active ? 'rgba(233, 76, 23, 0.08)' : 'transparent',
                color: item.active ? 'primary.main' : 'text.primary',
                '&:hover': {
                  backgroundColor: item.active ? 'rgba(233, 76, 23, 0.14)' : 'rgba(0, 0, 0, 0.03)',
                },
                '&.Mui-selected': {
                  backgroundColor: 'rgba(233, 76, 23, 0.08)',
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: collapsed ? 0 : 36,
                  color: item.active ? 'primary.main' : '#64748B',
                  justifyContent: 'center',
                }}
              >
                {item.icon}
              </ListItemIcon>
              {!collapsed && (
                <>
                  <ListItemText
                    primary={item.label}
                    primaryTypographyProps={{
                      fontSize: '0.875rem',
                      fontWeight: item.active ? 600 : 500,
                    }}
                  />
                  {item.badge && (
                    <Chip
                      label={item.badge}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        backgroundColor: item.active ? 'primary.main' : '#E2E8F0',
                        color: item.active ? '#FFFFFF' : '#475569',
                      }}
                    />
                  )}
                </>
              )}
            </ListItemButton>
          );

          return collapsed ? (
            <Tooltip key={item.label} title={item.label} placement="right" arrow>
              <ListItem disablePadding sx={{ display: 'block' }}>
                {button}
              </ListItem>
            </Tooltip>
          ) : (
            <ListItem key={item.label} disablePadding sx={{ display: 'block' }}>
              {button}
            </ListItem>
          );
        })}
      </List>

      <Divider />

      {/* Collapse Toggle Footer (Desktop only) */}
      <Box
        sx={{
          p: 1.5,
          display: { xs: 'none', md: 'flex' },
          justifyContent: collapsed ? 'center' : 'flex-end',
          alignItems: 'center',
        }}
      >
        <Tooltip title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'} arrow>
          <IconButton
            onClick={onToggleCollapse}
            size="small"
            sx={{
              border: '1px solid #E2E8F0',
              borderRadius: 2,
              backgroundColor: '#F8FAFC',
              '&:hover': { backgroundColor: '#F1F5F9' },
            }}
          >
            {collapsed ? <ChevronRightRoundedIcon fontSize="small" /> : <ChevronLeftRoundedIcon fontSize="small" />}
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );

  return (
    <>
      {/* Mobile Drawer */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onMobileClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Desktop Persistent Drawer */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', md: 'block' },
          width: collapsed ? COLLAPSED_WIDTH : DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: collapsed ? COLLAPSED_WIDTH : DRAWER_WIDTH,
            transition: 'width 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
            overflowX: 'hidden',
            boxSizing: 'border-box',
          },
        }}
        open
      >
        {drawerContent}
      </Drawer>
    </>
  );
}

