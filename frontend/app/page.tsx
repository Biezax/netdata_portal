'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import TabSwitcher from './components/TabSwitcher';
import HostsSidebar from './components/HostsSidebar';
import DashboardView from './components/DashboardView';
import AlertsView from './components/AlertsView';
import ErrorPage from './components/ErrorPage';

type ViewMode = 'hosts' | 'alerts';

interface Host {
  name: string;
  url: string;
  status: {
    reachable: boolean;
    alert_count: number;
    last_check: string | null;
    error_message: string | null;
  };
}

function HomeContent() {
  const searchParams = useSearchParams();
  const [viewMode, setViewMode] = useState<ViewMode>(
    (searchParams.get('view') as ViewMode) || 'hosts'
  );
  const [selectedHost, setSelectedHost] = useState<string | null>(searchParams.get('host'));
  const [hosts, setHosts] = useState<Host[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHosts = async () => {
      try {
        const response = await fetch('/api/hosts');
        const data = await response.json();
        setHosts(data.hosts || []);

        if (!selectedHost && data.hosts.length > 0) {
          setSelectedHost(data.hosts[0].name);
        }
      } catch (error) {
        console.error('Failed to fetch hosts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHosts();
    const interval = setInterval(fetchHosts, 20000);
    return () => clearInterval(interval);
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

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-netdata-bg text-netdata-text-muted">
        Loading...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-netdata-bg">
      <header className="h-14 px-4 flex items-center border-b border-netdata-border bg-netdata-bg">
        <TabSwitcher activeTab={viewMode} onTabChange={setViewMode} />
      </header>

      <main className="flex-1 p-4 flex gap-4 overflow-hidden">
        {viewMode === 'hosts' ? (
          <>
            <HostsSidebar
              hosts={hosts}
              selectedHost={selectedHost}
              onSelectHost={setSelectedHost}
            />
            {selectedHost ? (
              <DashboardView hostname={selectedHost} />
            ) : (
              <div className="flex-1 flex items-center justify-center bg-netdata-bg rounded-2xl border border-netdata-border">
                <ErrorPage
                  message="No host selected"
                  details="Please select a host from the sidebar to view its dashboard"
                />
              </div>
            )}
          </>
        ) : (
          <AlertsView />
        )}
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="flex-1 flex items-center justify-center bg-netdata-bg text-netdata-text-muted">Loading...</div>}>
      <HomeContent />
    </Suspense>
  );
}
