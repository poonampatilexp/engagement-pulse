'use client';

import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

function getWebSocketBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL.replace(/\/+$/, '');
  }
  if (process.env.NEXT_PUBLIC_API_URL) {
    const wsProto = process.env.NEXT_PUBLIC_API_URL.startsWith('https') ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_API_URL.replace(/^https?:\/\//, '').replace(/\/+$/, '');
    return `${wsProto}//${host}`;
  }
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.port === '3000'
      ? `${window.location.hostname}:8000`
      : window.location.host;
    return `${proto}//${host}`;
  }
  return 'ws://127.0.0.1:8000';
}

/**
 * Custom hook to establish and maintain a secure WebSocket connection for live updates
 * to the currently selected organisation.
 *
 * Requirements:
 * 1. Requests a single-use ticket from POST /api/auth/ws-ticket/
 * 2. Connects to /ws/organisations/<organisation_id>/updates/?ticket=<ticket>
 * 3. Invalidates React Query caches for projects and risks upon receiving 'data_changed'
 * 4. Maintains strictly one connection for the active organisation
 * 5. Cleans up previous connection when organisation changes or component unmounts
 * 6. Handles reconnection with fresh tickets on abnormal disconnects
 */
export function useOrganisationUpdates(organisationId?: number | null) {
  const queryClient = useQueryClient();
  const activeWsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!organisationId || typeof window === 'undefined' || typeof WebSocket === 'undefined') {
      return;
    }

    let isCancelled = false;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    let ws: WebSocket | null = null;

    async function establishConnection() {
      try {
        // Request short-lived single-use ticket from authenticated API endpoint
        const { ticket } = await apiClient.auth.getWebSocketTicket();
        if (isCancelled) return;

        const baseUrl = getWebSocketBaseUrl();
        const wsUrl = `${baseUrl}/ws/organisations/${organisationId}/updates/?ticket=${encodeURIComponent(ticket)}`;

        ws = new WebSocket(wsUrl);
        activeWsRef.current = ws;

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data?.type === 'data_changed') {
              // Invalidate React Query caches so project metrics and risk lists refetch automatically
              queryClient.invalidateQueries({ queryKey: ['projects', organisationId] });
              queryClient.invalidateQueries({ queryKey: ['risks'] });
            }
          } catch {
            // Ignore non-JSON frames
          }
        };

        ws.onclose = (event) => {
          if (activeWsRef.current === ws) {
            activeWsRef.current = null;
          }
          // Do not attempt to reconnect if unmounted, closed cleanly (code 1000),
          // or rejected due to auth/permission errors (4401: Unauthorized, 4403: Forbidden)
          if (!isCancelled && event.code !== 1000 && event.code !== 4401 && event.code !== 4403) {
            reconnectTimeout = setTimeout(() => {
              if (!isCancelled) {
                establishConnection();
              }
            }, 3000);
          }
        };

        ws.onerror = () => {
          // Socket errors lead to onclose where retry is handled
        };
      } catch {
        // If ticket retrieval failed, retry after delay
        if (!isCancelled) {
          reconnectTimeout = setTimeout(() => {
            if (!isCancelled) {
              establishConnection();
            }
          }, 5000);
        }
      }
    }

    establishConnection();

    return () => {
      isCancelled = true;
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (ws) {
        // Clean disconnect
        ws.close(1000, 'Organisation changed or component unmounted');
        if (activeWsRef.current === ws) {
          activeWsRef.current = null;
        }
      }
    };
  }, [organisationId, queryClient]);

  return activeWsRef;
}

