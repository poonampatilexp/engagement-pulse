'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { UserProfile, LoginResponse, OrganisationRef } from '@/types/auth';
import { apiClient } from '@/lib/api-client';

interface AuthContextType {
  user: UserProfile | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  selectedOrganisation: OrganisationRef | null;
  setSelectedOrganisation: (org: OrganisationRef) => void;
  availableOrganisations: OrganisationRef[];
  login: (data: LoginResponse) => void;
  logout: () => Promise<void>;
  refreshSession: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  // In-memory authentication state (never stored in localStorage or sessionStorage)
  const [user, setUser] = useState<UserProfile | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedOrganisation, setSelectedOrganisation] = useState<OrganisationRef | null>(null);

  const availableOrganisations: OrganisationRef[] = useMemo(() => {
    if (!user) return [];
    if (user.role === 'client_viewer') {
      return user.organisation ? [user.organisation] : [];
    }
    return user.organisations || [];
  }, [user]);

  // Sync selectedOrganisation when availableOrganisations change
  useEffect(() => {
    if (availableOrganisations.length > 0) {
      setSelectedOrganisation((prev) => {
        if (prev && availableOrganisations.some((org) => org.id === prev.id)) {
          return prev;
        }
        return availableOrganisations[0];
      });
    } else {
      setSelectedOrganisation(null);
    }
  }, [availableOrganisations]);

  const login = useCallback((data: LoginResponse) => {
    setAccessToken(data.access);
    setUser(data.user);
    apiClient.setAccessToken(data.access);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.auth.logout();
    } catch {
      // Ignore network errors during logout
    } finally {
      setAccessToken(null);
      setUser(null);
      setSelectedOrganisation(null);
      apiClient.setAccessToken(null);
      // Completely wipe TanStack React Query cache to prevent data leakage
      queryClient.clear();
      router.replace('/login');
    }
  }, [queryClient, router]);

  const refreshSession = useCallback(async (): Promise<boolean> => {
    try {
      const { access } = await apiClient.auth.refreshToken();
      setAccessToken(access);
      apiClient.setAccessToken(access);

      const profile = await apiClient.auth.getMe();
      setUser(profile);
      return true;
    } catch {
      setAccessToken(null);
      setUser(null);
      setSelectedOrganisation(null);
      apiClient.setAccessToken(null);
      return false;
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    // Register global callbacks for the API client
    apiClient.setOnTokenRefreshed((newToken) => {
      if (isMounted) {
        setAccessToken(newToken);
      }
    });

    apiClient.setOnAuthFailure(() => {
      if (isMounted) {
        setAccessToken(null);
        setUser(null);
        setSelectedOrganisation(null);
        apiClient.setAccessToken(null);
        queryClient.clear();
        router.replace('/login');
      }
    });

    // Session restoration on initial mount (browser refresh or initial visit)
    const initAuth = async () => {
      try {
        const { access } = await apiClient.auth.refreshToken();
        if (!isMounted) return;
        setAccessToken(access);
        apiClient.setAccessToken(access);

        const profile = await apiClient.auth.getMe();
        if (!isMounted) return;
        setUser(profile);
      } catch {
        if (isMounted) {
          setAccessToken(null);
          setUser(null);
          setSelectedOrganisation(null);
          apiClient.setAccessToken(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    initAuth();

    return () => {
      isMounted = false;
      apiClient.setOnTokenRefreshed(null);
      apiClient.setOnAuthFailure(null);
    };
  }, [queryClient, router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        isAuthenticated: !!accessToken && !!user,
        isLoading,
        selectedOrganisation,
        setSelectedOrganisation,
        availableOrganisations,
        login,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
