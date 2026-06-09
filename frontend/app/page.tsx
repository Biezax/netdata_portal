'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import HostsSidebar from './components/HostsSidebar';
import DashboardView from './components/DashboardView';
import AlertsView from './components/AlertsView';
import ErrorPage from './components/ErrorPage';
import { fetchJson } from './lib/fetchJson';

type ViewMode = 'hosts' | 'alerts';
type NotificationState = 'enabled' | 'silenced' | 'partial' | 'disabled' | 'unknown' | 'unavailable';

interface Host {
  name: string;
  url: string;
  status: {
    reachable: boolean;
    alert_count: number;
    critical_count: number;
    warning_count: number;
    last_check: string | null;
    error_message: string | null;
  };
}

interface HostNotificationStatus {
  state: NotificationState;
  message: string | null;
  retryable?: boolean;
}

const NOTIFICATION_STATES: NotificationState[] = [
  'enabled',
  'silenced',
  'partial',
  'disabled',
  'unknown',
  'unavailable',
];

async function fetchNotificationStatus(hostname: string): Promise<HostNotificationStatus> {
  try {
    const response = await fetchJson(`/api/hosts/${encodeURIComponent(hostname)}/notifications`);
    return await parseNotificationResponse(response);
  } catch {
    return {
      state: 'unavailable',
      message: 'Could not reach portal backend',
      retryable: true,
    };
  }
}

async function parseNotificationResponse(response: Response): Promise<HostNotificationStatus> {
  const data = await readJsonObject(response);

  if (response.status === 503 && data.error === 'ManagementDisabled') {
    return {
      state: 'unavailable',
      message: readDetail(data, 'Netdata management API is disabled'),
      retryable: false,
    };
  }

  if (response.status === 403 && data.error === 'ManagementForbidden') {
    return {
      state: 'unavailable',
      message: readDetail(data, 'Netdata management API rejected the request'),
      retryable: false,
    };
  }

  if (!response.ok) {
    return {
      state: 'unknown',
      message: readDetail(data, 'Could not read notification status'),
      retryable: true,
    };
  }

  const state = isNotificationState(data.state) ? data.state : 'unknown';
  return {
    state,
    message: typeof data.message === 'string'
      ? data.message
      : state === 'unknown' ? 'Notification status is unknown' : null,
    retryable: data.retryable === true,
  };
}

async function readJsonObject(response: Response): Promise<Record<string, unknown>> {
  try {
    const data = await response.json();
    return data && typeof data === 'object' && !Array.isArray(data) ? data : {};
  } catch {
    return {};
  }
}

function readDetail(data: Record<string, unknown>, fallback: string) {
  return typeof data.detail === 'string' ? data.detail : fallback;
}

function isNotificationState(value: unknown): value is NotificationState {
  return typeof value === 'string' && NOTIFICATION_STATES.includes(value as NotificationState);
}

function HomeContent() {
  const searchParams = useSearchParams();
  const [viewMode, setViewMode] = useState<ViewMode>(
    searchParams.get('view') === 'alerts' ? 'alerts' : 'hosts'
  );
  const [selectedHost, setSelectedHost] = useState<string | null>(searchParams.get('host'));
  const [hosts, setHosts] = useState<Host[]>([]);
  const [notificationStatuses, setNotificationStatuses] = useState<Record<string, HostNotificationStatus>>({});
  const [notificationBusy, setNotificationBusy] = useState<Record<string, boolean>>({});
  const notificationRequestedRef = useRef<Record<string, boolean>>({});
  const notificationInFlightRef = useRef<Record<string, boolean>>({});
  const notificationBusyRef = useRef<Record<string, boolean>>({});
  const notificationVersionRef = useRef<Record<string, number>>({});
  const hostReachabilityRef = useRef<Record<string, boolean | undefined>>({});
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<string | null>(null);

  useEffect(() => {
    fetchJson('/api/auth/me')
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => data && setUser(data.user))
      .catch(() => {});
  }, []);

  useEffect(() => {
    let stopped = false;

    const fetchHosts = async () => {
      try {
        const response = await fetchJson('/api/hosts');
        if (!response.ok) return;
        const data = await response.json();
        const nextHosts = sortHosts(data.hosts || []);
        if (stopped) return;

        setHosts(nextHosts);
        const nextHostnames: string[] = nextHosts.map((host: Host) => host.name);
        const nextHostnameSet = new Set<string>(nextHostnames);
        notificationRequestedRef.current = pickMap(notificationRequestedRef.current, nextHostnameSet);
        notificationInFlightRef.current = pickMap(notificationInFlightRef.current, nextHostnameSet);
        notificationBusyRef.current = pickMap(notificationBusyRef.current, nextHostnameSet);
        notificationVersionRef.current = pickMap(notificationVersionRef.current, nextHostnameSet);
        hostReachabilityRef.current = syncHostReachability(
          hostReachabilityRef.current,
          nextHosts,
          notificationRequestedRef,
          notificationVersionRef
        );
        setNotificationBusy((current) => pickMap(current, nextHostnameSet));
        setNotificationStatuses((current) => syncNotificationHosts(current, nextHostnames));

        setSelectedHost((current) => {
          if (current && nextHosts.some((host: Host) => host.name === current)) {
            return current;
          }
          return nextHosts[0]?.name || null;
        });
      } catch (error) {
        console.error('Failed to fetch hosts:', error);
      } finally {
        if (!stopped) {
          setLoading(false);
        }
      }
    };

    fetchHosts();
    const interval = setInterval(fetchHosts, 20000);
    return () => {
      stopped = true;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    let stopped = false;
    const hostnames = hosts
      .map((host) => host.name)
      .filter((hostname) => (
        !notificationRequestedRef.current[hostname] &&
        !notificationInFlightRef.current[hostname]
      ));

    if (hostnames.length === 0) return;

    for (const hostname of hostnames) {
      notificationInFlightRef.current[hostname] = true;
    }

    const requests = hostnames.map((hostname) => ({
      hostname,
      version: notificationVersionRef.current[hostname] || 0,
    }));

    Promise.all(
      requests.map(async ({ hostname, version }) => [
        hostname,
        version,
        await fetchNotificationStatus(hostname),
      ] as const)
    ).then((statuses) => {
      if (stopped) return;

      setNotificationStatuses((current) => {
        const next = { ...current };
        for (const [hostname, version, status] of statuses) {
          delete notificationInFlightRef.current[hostname];
          if (notificationBusyRef.current[hostname]) {
            continue;
          }

          if (hostReachabilityRef.current[hostname] === false) {
            const nextStatus = status.state === 'unavailable' && status.retryable === false
              ? status
              : hostUnreachableNotificationStatus();
            next[hostname] = nextStatus;
            if (nextStatus.retryable) {
              delete notificationRequestedRef.current[hostname];
            } else {
              notificationRequestedRef.current[hostname] = true;
            }
            continue;
          }

          if (version === (notificationVersionRef.current[hostname] || 0)) {
            next[hostname] = status;
            if (status.retryable) {
              delete notificationRequestedRef.current[hostname];
            } else {
              notificationRequestedRef.current[hostname] = true;
            }
          }
        }
        return next;
      });
    });

    return () => {
      stopped = true;
      for (const hostname of hostnames) {
        delete notificationInFlightRef.current[hostname];
      }
    };
  }, [hosts]);

  useEffect(() => {
    if (!selectedHost) return;

    let stopped = false;

    const refreshSelectedHost = async () => {
      if (notificationBusyRef.current[selectedHost] || notificationInFlightRef.current[selectedHost]) return;

      notificationInFlightRef.current[selectedHost] = true;
      const version = notificationVersionRef.current[selectedHost] || 0;
      try {
        const status = await fetchNotificationStatus(selectedHost);
        if (
          stopped ||
          notificationBusyRef.current[selectedHost]
        ) {
          return;
        }

        if (hostReachabilityRef.current[selectedHost] === false) {
          const nextStatus = status.state === 'unavailable' && status.retryable === false
            ? status
            : hostUnreachableNotificationStatus();
          setNotificationStatuses((current) => ({ ...current, [selectedHost]: nextStatus }));
          updateNotificationRequested(selectedHost, nextStatus);
          return;
        }

        if (version !== (notificationVersionRef.current[selectedHost] || 0)) {
          return;
        }

        setNotificationStatuses((current) => ({ ...current, [selectedHost]: status }));
        if (status.retryable) {
          delete notificationRequestedRef.current[selectedHost];
        } else {
          notificationRequestedRef.current[selectedHost] = true;
        }
      } finally {
        delete notificationInFlightRef.current[selectedHost];
      }
    };

    refreshSelectedHost();
    const interval = setInterval(refreshSelectedHost, 60000);
    return () => {
      stopped = true;
      clearInterval(interval);
    };
  }, [selectedHost]);

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set('view', viewMode);
    if (selectedHost) {
      url.searchParams.set('host', selectedHost);
    } else {
      url.searchParams.delete('host');
    }
    window.history.replaceState({}, '', url.toString());
  }, [viewMode, selectedHost]);

  const handleToggleNotifications = async (hostname: string) => {
    if (notificationBusyRef.current[hostname]) return;

    const state = notificationStatuses[hostname]?.state;
    const command = state === 'enabled'
      ? 'silence'
      : state === 'silenced' || state === 'partial' || state === 'disabled'
        ? 'reset'
        : null;

    if (!command) return;

    notificationVersionRef.current = {
      ...notificationVersionRef.current,
      [hostname]: (notificationVersionRef.current[hostname] || 0) + 1,
    };
    setNotificationBusyForHost(hostname, true);
    try {
      const response = await fetchJson(
        `/api/hosts/${encodeURIComponent(hostname)}/notifications/${command}`,
        { method: 'POST' }
      );
      const nextStatus = await parseNotificationResponse(response);
      updateNotificationRequested(hostname, nextStatus);
      setNotificationStatuses((current) => ({ ...current, [hostname]: nextStatus }));
    } catch {
      delete notificationRequestedRef.current[hostname];
      setNotificationStatuses((current) => ({
        ...current,
        [hostname]: {
          state: 'unavailable',
          message: 'Could not reach portal backend',
          retryable: true,
        },
      }));
    } finally {
      setNotificationBusyForHost(hostname, false);
    }
  };

  const setNotificationBusyForHost = (hostname: string, busy: boolean) => {
    notificationBusyRef.current = { ...notificationBusyRef.current, [hostname]: busy };
    setNotificationBusy((current) => ({ ...current, [hostname]: busy }));
  };

  const updateNotificationRequested = (hostname: string, status: HostNotificationStatus) => {
    if (status.retryable) {
      delete notificationRequestedRef.current[hostname];
    } else {
      notificationRequestedRef.current[hostname] = true;
    }
  };

  const handleSelectHost = (hostname: string) => {
    setSelectedHost(hostname);
    setViewMode('hosts');
  };

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.assign('/login');
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-netdata-bg text-netdata-text-muted">
        Loading...
      </div>
    );
  }

  return (
    <div className="relative h-screen overflow-hidden bg-netdata-darker">
      <main className="absolute inset-0 overflow-hidden">
        {viewMode === 'hosts' ? (
          selectedHost ? (
            <DashboardView key={selectedHost} hostname={selectedHost} />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-netdata-bg">
              <ErrorPage
                message="No host selected"
                details="Please select a host from the sidebar to view its dashboard"
              />
            </div>
          )
        ) : (
          <div className="absolute inset-0 p-4 pt-16 md:pt-4">
            <AlertsView />
          </div>
        )}
        <HostsSidebar
          hosts={hosts}
          selectedHost={selectedHost}
          onSelectHost={handleSelectHost}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          notificationStatuses={notificationStatuses}
          notificationBusy={notificationBusy}
          onToggleNotifications={handleToggleNotifications}
          user={user}
          onLogout={handleLogout}
        />
      </main>
    </div>
  );
}

function syncNotificationHosts(
  current: Record<string, HostNotificationStatus>,
  hostnames: string[]
) {
  let changed = false;
  const next: Record<string, HostNotificationStatus> = {};

  for (const hostname of hostnames) {
    if (current[hostname]) {
      next[hostname] = current[hostname];
    } else {
      changed = true;
      next[hostname] = {
        state: 'unknown',
        message: 'Loading notification status',
      };
    }
  }

  if (Object.keys(current).length !== hostnames.length) {
    changed = true;
  }

  return changed ? next : current;
}

function sortHosts(hosts: Host[]) {
  return [...hosts].sort(compareHosts);
}

function syncHostReachability(
  current: Record<string, boolean | undefined>,
  hosts: Host[],
  notificationRequestedRef: { current: Record<string, boolean> },
  notificationVersionRef: { current: Record<string, number> }
) {
  const next: Record<string, boolean | undefined> = {};
  let nextVersions = notificationVersionRef.current;

  for (const host of hosts) {
    const reachable = getKnownHostReachability(host);
    next[host.name] = reachable;

    if (reachable !== undefined && current[host.name] !== reachable) {
      delete notificationRequestedRef.current[host.name];
      nextVersions = {
        ...nextVersions,
        [host.name]: (nextVersions[host.name] || 0) + 1,
      };
    }
  }

  notificationVersionRef.current = nextVersions;
  return next;
}

function getKnownHostReachability(host: Host) {
  return host.status.last_check === null ? undefined : host.status.reachable;
}

function hostUnreachableNotificationStatus(): HostNotificationStatus {
  return {
    state: 'unavailable',
    message: 'Host is unreachable',
    retryable: true,
  };
}

function compareHosts(a: Host, b: Host) {
  const groupDiff = getHostSortGroup(a) - getHostSortGroup(b);
  if (groupDiff !== 0) return groupDiff;

  const criticalDiff = (b.status.critical_count ?? 0) - (a.status.critical_count ?? 0);
  if (criticalDiff !== 0) return criticalDiff;

  const warningDiff = (b.status.warning_count ?? 0) - (a.status.warning_count ?? 0);
  if (warningDiff !== 0) return warningDiff;

  return a.name.localeCompare(b.name, undefined, { numeric: true });
}

function getHostSortGroup(host: Host) {
  if (!host.status.reachable) return 3;
  if ((host.status.critical_count ?? 0) > 0) return 0;
  if ((host.status.warning_count ?? 0) > 0) return 1;
  return 2;
}

function pickMap<T>(current: Record<string, T>, allowed: Set<string>) {
  let changed = false;
  const next: Record<string, T> = {};

  for (const [key, value] of Object.entries(current)) {
    if (allowed.has(key)) {
      next[key] = value;
    } else {
      changed = true;
    }
  }

  return changed ? next : current;
}

export default function Home() {
  return (
    <Suspense fallback={<div className="flex-1 flex items-center justify-center bg-netdata-bg text-netdata-text-muted">Loading...</div>}>
      <HomeContent />
    </Suspense>
  );
}
