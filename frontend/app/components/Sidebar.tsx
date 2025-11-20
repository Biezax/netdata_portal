'use client';

import { useEffect, useState } from 'react';

interface Host {
  name: string;
  url: string;
  status: {
    reachable: boolean;
    last_check: string | null;
    alert_count: number;
    error_message: string | null;
  };
}

interface SidebarProps {
  selectedHost: string | null;
  onSelectHost: (hostname: string) => void;
}

export default function Sidebar({ selectedHost, onSelectHost }: SidebarProps) {
  const [hosts, setHosts] = useState<Host[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHosts = async () => {
      try {
        const response = await fetch('/api/hosts');
        const data = await response.json();
        setHosts(data.hosts);
      } catch (error) {
        console.error('Failed to fetch hosts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHosts();
    const interval = setInterval(fetchHosts, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="w-64 bg-netdata-darker border-r border-netdata-border p-4">
        <h2 className="text-lg font-bold text-netdata-accent mb-4">Hosts</h2>
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="w-64 bg-netdata-darker border-r border-netdata-border p-4">
      <h2 className="text-lg font-bold text-netdata-accent mb-4">Netdata Hosts</h2>
      <div className="space-y-2">
        {hosts.map((host) => (
          <button
            key={host.name}
            onClick={() => onSelectHost(host.name)}
            className={`w-full text-left p-3 rounded transition-colors ${
              selectedHost === host.name
                ? 'bg-netdata-accent text-white'
                : 'bg-netdata-dark hover:bg-gray-800'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium">{host.name}</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  host.status.reachable ? 'bg-netdata-accent' : 'bg-netdata-critical'
                }`}
              />
            </div>
            {host.status.alert_count > 0 && (
              <div className="text-xs text-netdata-warning mt-1">
                {host.status.alert_count} alert{host.status.alert_count > 1 ? 's' : ''}
              </div>
            )}
            {host.status.error_message && (
              <div className="text-xs text-netdata-critical mt-1">{host.status.error_message}</div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
