'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  InputAdornment,
  IconButton,
  CircularProgress,
  Chip,
  Divider,
} from '@mui/material';
import VisibilityRoundedIcon from '@mui/icons-material/VisibilityRounded';
import VisibilityOffRoundedIcon from '@mui/icons-material/VisibilityOffRounded';
import PulseIcon from '@mui/icons-material/TimelineRounded';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import { apiClient, ApiClientError } from '@/lib/api-client';
import { useAuth } from '@/context/AuthContext';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Field validation errors
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');

  const validate = (): boolean => {
    let isValid = true;

    if (!email.trim()) {
      setEmailError('Email address is required.');
      isValid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setEmailError('Please enter a valid email address.');
      isValid = false;
    } else {
      setEmailError('');
    }

    if (!password) {
      setPasswordError('Password is required.');
      isValid = false;
    } else {
      setPasswordError('');
    }

    return isValid;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!validate()) {
      return;
    }

    setLoading(true);

    try {
      // Connect to real Django backend: POST /api/auth/login/
      const data = await apiClient.auth.login({
        email: email.trim(),
        password,
      });

      // Save token and user in purely in-memory React state
      login(data);

      // Navigate to existing dashboard
      router.push('/');
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('An unexpected network error occurred. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFillDemo = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword('');
    setEmailError('');
    setPasswordError('');
    setErrorMessage(null);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#F8FAFC',
        p: { xs: 2, sm: 3 },
      }}
    >
      <Card
        sx={{
          width: '100%',
          maxWidth: 440,
          borderRadius: 3,
          border: '1px solid #E2E8F0',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
        }}
      >
        <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
          {/* Brand Header */}
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 3 }}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: 2.5,
                backgroundColor: 'primary.main',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#FFFFFF',
                boxShadow: '0 4px 10px rgba(233, 76, 23, 0.3)',
                mb: 1.5,
              }}
            >
              <PulseIcon sx={{ fontSize: 28 }} />
            </Box>
            <Typography variant="h3" sx={{ fontWeight: 700, color: '#0F172A', textAlign: 'center' }}>
              Engagement Pulse
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5, textAlign: 'center' }}>
              Sign in to manage projects and engagement risks
            </Typography>
          </Box>

          {/* Error Alert */}
          {errorMessage && (
            <Alert
              severity="error"
              sx={{
                mb: 3,
                borderRadius: 2,
                fontSize: '0.875rem',
              }}
              onClose={() => setErrorMessage(null)}
            >
              {errorMessage}
            </Alert>
          )}

          {/* Login Form */}
          <Box component="form" onSubmit={handleSubmit} noValidate>
            <Box sx={{ mb: 2.5 }}>
              <TextField
                id="email"
                name="email"
                label="Email Address"
                type="email"
                fullWidth
                autoComplete="email"
                autoFocus
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (emailError) setEmailError('');
                }}
                error={!!emailError}
                helperText={emailError}
                disabled={loading}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <EmailOutlinedIcon fontSize="small" sx={{ color: '#94A3B8' }} />
                    </InputAdornment>
                  ),
                }}
              />
            </Box>

            <Box sx={{ mb: 3 }}>
              <TextField
                id="password"
                name="password"
                label="Password"
                type={showPassword ? 'text' : 'password'}
                fullWidth
                autoComplete="current-password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (passwordError) setPasswordError('');
                }}
                error={!!passwordError}
                helperText={passwordError}
                disabled={loading}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <LockOutlinedIcon fontSize="small" sx={{ color: '#94A3B8' }} />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle password visibility"
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                        size="small"
                      >
                        {showPassword ? (
                          <VisibilityOffRoundedIcon fontSize="small" />
                        ) : (
                          <VisibilityRoundedIcon fontSize="small" />
                        )}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Box>

            <Button
              type="submit"
              variant="contained"
              fullWidth
              size="large"
              disabled={loading}
              sx={{
                py: 1.25,
                fontWeight: 700,
                fontSize: '0.95rem',
              }}
            >
              {loading ? (
                <CircularProgress size={24} sx={{ color: '#FFFFFF' }} />
              ) : (
                'Sign In'
              )}
            </Button>
          </Box>

          <Divider sx={{ my: 3 }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>
              SEEDED DEMO LOGINS
            </Typography>
          </Divider>

          {/* Quick Demo Credentials Autofill */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Box
              sx={{
                p: 1.25,
                borderRadius: 2,
                border: '1px solid #E2E8F0',
                backgroundColor: '#FFFFFF',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                transition: 'all 0.15s',
                '&:hover': { borderColor: 'primary.light', bgcolor: '#FFF7ED' },
              }}
            >
              <Box>
                <Typography variant="caption" sx={{ fontWeight: 700, color: '#0F172A', display: 'block' }}>
                  Consultant
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  consultant@engagementpulse.com
                </Typography>
              </Box>
              <Chip
                label="Auto-fill"
                size="small"
                clickable
                onClick={() => handleFillDemo('consultant@engagementpulse.com')}
                sx={{
                  fontWeight: 600,
                  fontSize: '0.7rem',
                  bgcolor: '#FFF3EE',
                  color: 'primary.main',
                  border: '1px solid #FECBB8',
                }}
              />
            </Box>

            <Box
              sx={{
                p: 1.25,
                borderRadius: 2,
                border: '1px solid #E2E8F0',
                backgroundColor: '#FFFFFF',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                transition: 'all 0.15s',
                '&:hover': { borderColor: 'primary.light', bgcolor: '#FFF7ED' },
              }}
            >
              <Box>
                <Typography variant="caption" sx={{ fontWeight: 700, color: '#0F172A', display: 'block' }}>
                  Client Viewer (Acme Health)
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  viewer.acme@example.com
                </Typography>
              </Box>
              <Chip
                label="Auto-fill"
                size="small"
                clickable
                onClick={() => handleFillDemo('viewer.acme@example.com')}
                sx={{
                  fontWeight: 600,
                  fontSize: '0.7rem',
                  bgcolor: '#F1F5F9',
                  color: '#475569',
                  border: '1px solid #CBD5E1',
                }}
              />
            </Box>

            <Box
              sx={{
                p: 1.25,
                borderRadius: 2,
                border: '1px solid #E2E8F0',
                backgroundColor: '#FFFFFF',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                transition: 'all 0.15s',
                '&:hover': { borderColor: 'primary.light', bgcolor: '#FFF7ED' },
              }}
            >
              <Box>
                <Typography variant="caption" sx={{ fontWeight: 700, color: '#0F172A', display: 'block' }}>
                  Client Viewer (Beta Care)
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  viewer.beta@example.com
                </Typography>
              </Box>
              <Chip
                label="Auto-fill"
                size="small"
                clickable
                onClick={() => handleFillDemo('viewer.beta@example.com')}
                sx={{
                  fontWeight: 600,
                  fontSize: '0.7rem',
                  bgcolor: '#F1F5F9',
                  color: '#475569',
                  border: '1px solid #CBD5E1',
                }}
              />
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}

