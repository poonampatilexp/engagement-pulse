import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useOrganisationUpdates, getWebSocketBaseUrl } from '@/hooks/useOrganisationUpdates';
import { apiClient } from '@/lib/api-client';

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onmessage: ((event: any) => void) | null = null;
  onclose: ((event: any) => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  close = jest.fn((code = 1000, reason = '') => {
    if (this.onclose) {
      this.onclose({ code, reason });
    }
  });

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }
}

describe('Live Dashboard Updates & WebSocket Hook', () => {
  let queryClient: QueryClient;
  const originalWebSocket = global.WebSocket;

  beforeEach(() => {
    jest.clearAllMocks();
    MockWebSocket.instances = [];
    (global as any).WebSocket = MockWebSocket;
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    jest.spyOn(apiClient.auth, 'getWebSocketTicket').mockResolvedValue({
      ticket: 'mock-ws-ticket-uuid',
      expires_in: 30,
    });
  });

  afterEach(() => {
    (global as any).WebSocket = originalWebSocket;
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('requests a ticket and connects to the correct organisation websocket endpoint', async () => {
    renderHook(() => useOrganisationUpdates(1), { wrapper });

    await waitFor(() => {
      expect(apiClient.auth.getWebSocketTicket).toHaveBeenCalledTimes(1);
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const wsInstance = MockWebSocket.instances[0];
    expect(wsInstance.url).toContain('/ws/organisations/1/updates/?ticket=mock-ws-ticket-uuid');
  });

  it('invalidates React Query caches for projects and risks when receiving data_changed', async () => {
    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    renderHook(() => useOrganisationUpdates(1), { wrapper });

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const wsInstance = MockWebSocket.instances[0];

    act(() => {
      wsInstance.onmessage?.({
        data: JSON.stringify({
          type: 'data_changed',
          organisation_id: 1,
          project_id: 10,
        }),
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['projects', 1] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['risks'] });
  });

  it('closes the connection cleanly when the component unmounts', async () => {
    const { unmount } = renderHook(() => useOrganisationUpdates(1), { wrapper });

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const wsInstance = MockWebSocket.instances[0];

    unmount();

    expect(wsInstance.close).toHaveBeenCalledWith(
      1000,
      'Organisation changed or component unmounted'
    );
  });

  it('closes previous connection and reconnects when organisation changes', async () => {
    let orgId = 1;
    const { rerender } = renderHook(() => useOrganisationUpdates(orgId), { wrapper });

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const firstWs = MockWebSocket.instances[0];
    expect(firstWs.url).toContain('/ws/organisations/1/updates/');

    // Switch organisation to Globex (id 2)
    orgId = 2;
    rerender();

    await waitFor(() => {
      expect(firstWs.close).toHaveBeenCalledWith(
        1000,
        'Organisation changed or component unmounted'
      );
      expect(MockWebSocket.instances.length).toBe(2);
    });

    const secondWs = MockWebSocket.instances[1];
    expect(secondWs.url).toContain('/ws/organisations/2/updates/');
  });

  it('attempts reconnection with fresh ticket on abnormal disconnection', async () => {
    jest.useFakeTimers();

    renderHook(() => useOrganisationUpdates(1), { wrapper });

    await act(async () => {
      await Promise.resolve();
    });

    expect(MockWebSocket.instances.length).toBe(1);
    const firstWs = MockWebSocket.instances[0];

    // Trigger unexpected close (code 1006)
    act(() => {
      firstWs.onclose?.({ code: 1006, reason: 'Network lost' });
    });

    // Advance reconnection timer
    await act(async () => {
      jest.advanceTimersByTime(3500);
      await Promise.resolve();
    });

    expect(apiClient.auth.getWebSocketTicket).toHaveBeenCalledTimes(2);
    expect(MockWebSocket.instances.length).toBe(2);

    jest.useRealTimers();
  });

  it('resolves backend WebSocket URL to port 8000 when frontend runs on port 3001 or 3000', () => {
    expect(getWebSocketBaseUrl({ protocol: 'http:', hostname: 'localhost', port: '3001', host: 'localhost:3001' }))
      .toBe('ws://localhost:8000');
    expect(getWebSocketBaseUrl({ protocol: 'http:', hostname: 'localhost', port: '3000', host: 'localhost:3000' }))
      .toBe('ws://localhost:8000');
    expect(getWebSocketBaseUrl({ protocol: 'http:', hostname: '127.0.0.1', port: '3001', host: '127.0.0.1:3001' }))
      .toBe('ws://127.0.0.1:8000');
    expect(getWebSocketBaseUrl({ protocol: 'https:', hostname: 'pulse.example.com', port: '443', host: 'pulse.example.com' }))
      .toBe('wss://pulse.example.com');
  });
});

