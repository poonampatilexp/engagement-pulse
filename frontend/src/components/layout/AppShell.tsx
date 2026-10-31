'use client';

import React, { useState, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Box, Container, CircularProgress, Typography } from '@mui/material';
import Sidebar from './Sidebar';
import Header from './Header';
import { useAuth } from '@/context/AuthContext';

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const isLoginPage = pathname === '/login';

  // Route protection effect
  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated && !isLoginPage) {
      router.replace('/login');
    } else if (isAuthenticated && isLoginPage) {
      router.replace('/');
    }
  }, [isAuthenticated, isLoading, isLoginPage, router]);

  // 1. While resolving initial authentication, render loading spinner to prevent content flashing
  if (isLoading) {
    return (
      <Box
        data-testid="auth-loading-state"
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#F8FAFC',
          gap: 2,
        }}
      >
        <CircularProgress size={42} sx={{ color: 'primary.main' }} />
        <Typography variant="body2" sx={{ color: 'text.secondary', fontWeight: 500 }}>
          Authenticating session...
        </Typography>
      </Box>
    );
  }

  // 2. Unauthenticated user on a protected route: render empty state while redirecting to /login
  if (!isAuthenticated && !isLoginPage) {
    return null;
  }

  // 3. Authenticated user visiting /login: render empty state while redirecting to /
  if (isAuthenticated && isLoginPage) {
    return null;
  }

  // 4. Unauthenticated user on /login: render authentication view without dashboard shell
  if (isLoginPage) {
    return (
      <Box
        component="main"
        sx={{
          minHeight: '100vh',
          backgroundColor: 'background.default',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {children}
      </Box>
    );
  }

  // 5. Authenticated user on protected dashboard routes: render full application shell
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', backgroundColor: 'background.default' }}>
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(!collapsed)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

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
        <Header onMobileDrawerToggle={() => setMobileOpen(!mobileOpen)} />
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
