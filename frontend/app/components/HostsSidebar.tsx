'use client';

import { useState } from 'react';

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

interface HostsSidebarProps {
  hosts: Host[];
  selectedHost: string | null;
  onSelectHost: (hostname: string) => void;
}

export default function HostsSidebar({ hosts, selectedHost, onSelectHost }: HostsSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredHosts = hosts.filter((host) =>
    host.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusColor = (host: Host) => {
    if (!host.status.reachable) return 'bg-netdata-critical';
    if (host.status.alert_count > 0) return 'bg-netdata-warning';
    return 'bg-netdata-accent';
  };

  return (
    <aside className="w-[280px] min-w-[240px] max-w-[320px] bg-netdata-bg rounded-2xl border border-netdata-border p-3 flex flex-col">
      <div className="text-sm font-medium mb-2 text-netdata-text-muted">Хосты</div>

      <div className="mb-2">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Фильтр по hostname"
          className="w-full px-2.5 py-1.5 rounded-full border border-netdata-border-dark bg-netdata-bg text-netdata-text-primary text-sm outline-none placeholder:text-netdata-text-dim"
        />
      </div>

      <ul className="overflow-y-auto flex-1 mt-1 space-y-0.5">
        {filteredHosts.map((host) => (
          <li
            key={host.name}
            onClick={() => onSelectHost(host.name)}
            className={`px-2.5 py-2 rounded-lg text-sm cursor-pointer flex items-center justify-between transition-all ${
              selectedHost === host.name
                ? 'bg-netdata-accent-dim text-netdata-accent-light'
                : 'hover:bg-netdata-panel-bg text-netdata-text-primary'
            }`}
          >
            <span>{host.name}</span>
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${getStatusColor(host)}`} />
          </li>
        ))}
      </ul>
    </aside>
  );
}
