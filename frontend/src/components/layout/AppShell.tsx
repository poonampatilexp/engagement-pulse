'use client';

import React, { useState } from 'react';
import { Box, Container } from '@mui/material';
import Sidebar, { DRAWER_WIDTH, COLLAPSED_WIDTH } from './Sidebar';
import Header from './Header';

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleToggleCollapse = () => {
    setCollapsed(!collapsed);
  };

  const handleMobileToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', backgroundColor: 'background.default' }}>
      {/* Navigation Sidebar */}
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={handleToggleCollapse}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {/* Main Content Workspace */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0,
          transition: 'margin-left 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        <Header onMobileDrawerToggle={handleMobileToggle} />
        <Container
          maxWidth="xl"
          sx={{
            py: { xs: 3, sm: 4 },
            px: { xs: 2, sm: 3, md: 4 },
            flexGrow: 1,
          }}
        >
          {children}
        </Container>
      </Box>
    </Box>
  );
}

