'use client';

import { useCallback, useEffect, useState } from 'react';
import { fetchJson } from '../lib/fetchJson';

interface DashboardViewProps {
  hostname: string;
}

type NotificationState = 'enabled' | 'silenced' | 'partial' | 'disabled' | 'unknown' | 'unavailable';

interface NotificationStatus {
  state: NotificationState;
  silenced: boolean | null;
  raw: string;
}

export default function DashboardView({ hostname }: DashboardViewProps) {
  const proxyUrl = `/api/proxy/${encodeURIComponent(hostname)}/v3/`;
  const [notificationState, setNotificationState] = useState<NotificationState>('unknown');
  const [notificationMessage, setNotificationMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [managementAvailable, setManagementAvailable] = useState(true);

  const statusUrl = `/api/hosts/${encodeURIComponent(hostname)}/notifications`;

  const refreshStatus = useCallback(async (signal?: AbortSignal) => {
    try {
      const response = await fetchJson(statusUrl, { signal });
      const data = await response.json();
      if (signal?.aborted) {
        return;
      }

      if (response.status === 503 && data.error === 'ManagementDisabled') {
        setNotificationState('unavailable');
        setNotificationMessage(data.detail || 'Netdata management API is disabled');
        setManagementAvailable(false);
        return;
      }

      if (response.status === 403 && data.error === 'ManagementForbidden') {
        setNotificationState('unavailable');
        setNotificationMessage(data.detail || 'Netdata management API rejected the request');
        setManagementAvailable(false);
        return;
      }

      if (!response.ok) {
        setNotificationState('unknown');
        setNotificationMessage(data.detail || 'Could not read notification status');
        setManagementAvailable(true);
        return;
      }

      setNotificationState((data as NotificationStatus).state);
      setNotificationMessage(null);
      setManagementAvailable(true);
    } catch (error) {
      if (signal?.aborted || (error instanceof DOMException && error.name === 'AbortError')) {
        return;
      }
      setNotificationState('unavailable');
      setNotificationMessage('Could not reach portal backend');
      setManagementAvailable(false);
    }
  }, [statusUrl]);

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      refreshStatus(controller.signal);
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [refreshStatus]);

  const runManagementCommand = async (command: 'silence' | 'reset') => {
    setBusy(true);
    try {
      const response = await fetchJson(`${statusUrl}/${command}`, { method: 'POST' });
      if (response.status === 503) {
        const data = await response.json();
        if (data.error === 'ManagementDisabled') {
          setNotificationState('unavailable');
          setNotificationMessage(data.detail || 'Netdata management API is disabled');
          setManagementAvailable(false);
          return;
        }
      }
      if (response.status === 403) {
        const data = await response.json();
        if (data.error === 'ManagementForbidden') {
          setNotificationState('unavailable');
          setNotificationMessage(data.detail || 'Netdata management API rejected the request');
          setManagementAvailable(false);
          return;
        }
      }
      await refreshStatus();
    } catch {
      setNotificationState('unavailable');
      setNotificationMessage('Could not reach portal backend');
      setManagementAvailable(false);
    } finally {
      setBusy(false);
    }
  };

  const controlsDisabled = busy || !managementAvailable;

  return (
    <section className="flex-1 rounded-2xl border border-netdata-border overflow-hidden bg-netdata-bg flex flex-col">
      <div className="min-h-12 px-4 py-2 flex flex-wrap items-center gap-2 border-b border-netdata-border bg-netdata-bg-panel">
        <div className="min-w-0 flex-1 text-sm font-medium text-netdata-text-primary truncate">
          {hostname}
        </div>
        <span className={getBadgeClass(notificationState)}>
          {notificationState}
        </span>
        <button
          type="button"
          onClick={() => runManagementCommand('silence')}
          disabled={controlsDisabled || notificationState === 'silenced'}
          className="px-3 py-1.5 rounded-md border border-netdata-border-dark text-sm text-netdata-text-secondary whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed hover:border-netdata-accent hover:text-netdata-text-primary"
        >
          Silence notifications
        </button>
        <button
          type="button"
          onClick={() => runManagementCommand('reset')}
          disabled={controlsDisabled || notificationState === 'enabled'}
          className="px-3 py-1.5 rounded-md border border-netdata-border-dark text-sm text-netdata-text-secondary whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed hover:border-netdata-accent hover:text-netdata-text-primary"
        >
          Enable notifications
        </button>
        {notificationMessage && (
          <div className="basis-full text-xs text-netdata-warning">
            {notificationMessage}
          </div>
        )}
      </div>
      <div className="flex-1 min-h-0">
        <iframe
          src={proxyUrl}
          className="w-full h-full border-0"
          title={`Netdata dashboard for ${hostname}`}
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
          allow="fullscreen"
        />
      </div>
    </section>
  );
}

function getBadgeClass(state: NotificationState) {
  const base = 'px-2 py-1 rounded-md border text-xs font-semibold uppercase whitespace-nowrap';
  if (state === 'enabled') {
    return `${base} border-netdata-accent text-netdata-accent-light bg-netdata-accent-dim`;
  }
  if (state === 'silenced') {
    return `${base} border-netdata-warning text-netdata-warning bg-netdata-alert-warning`;
  }
  if (state === 'partial') {
    return `${base} border-netdata-warning text-netdata-warning bg-netdata-alert-warning`;
  }
  if (state === 'disabled') {
    return `${base} border-netdata-critical text-netdata-critical bg-netdata-alert-critical`;
  }
  if (state === 'unavailable') {
    return `${base} border-netdata-border-dark text-netdata-text-muted bg-netdata-dark`;
  }
  return `${base} border-netdata-border-dark text-netdata-text-muted bg-netdata-alert-info`;
}
