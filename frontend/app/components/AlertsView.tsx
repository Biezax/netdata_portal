'use client';

import { useEffect, useState } from 'react';

interface Alert {
  source_host: string;
  alert_id: string;
  name: string;
  severity: 'critical' | 'warning' | 'info';
  status: string;
  timestamp: string;
  value: number | null;
  message: string;
}

interface AlertsData {
  alerts: Alert[];
  total: number;
  by_severity: {
    critical: number;
    warning: number;
    info: number;
  };
  unreachable_hosts: string[];
}

export default function AlertsView() {
  const [alertsData, setAlertsData] = useState<AlertsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await fetch('/api/alerts');
        const data = await response.json();
        setAlertsData(data);
      } catch (error) {
        console.error('Failed to fetch alerts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 20000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityBg = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-netdata-alert-critical';
      case 'warning':
        return 'bg-netdata-alert-warning';
      case 'info':
        return 'bg-netdata-alert-info';
      default:
        return 'bg-netdata-panel-bg';
    }
  };

  const sortedAlerts = alertsData?.alerts.slice().sort((a, b) => {
    const severityOrder = { critical: 3, warning: 2, info: 1 };
    return severityOrder[b.severity] - severityOrder[a.severity];
  }) || [];

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-netdata-bg">
        <p className="text-netdata-text-muted">Loading alerts...</p>
      </div>
    );
  }

  if (!alertsData) {
    return (
      <div className="flex-1 flex items-center justify-center bg-netdata-bg">
        <p className="text-netdata-text-muted">Failed to load alerts</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex">
      <aside className="w-full bg-netdata-bg rounded-2xl border border-netdata-border p-3 flex flex-col overflow-hidden">
        <div className="mb-2">
          <div className="text-sm font-medium text-netdata-text-muted mb-2">
            Алерты (по важности)
          </div>
          <div className="flex gap-4 text-sm mb-2">
            <span className="text-netdata-critical">
              Critical: {alertsData.by_severity.critical}
            </span>
            <span className="text-netdata-warning">
              Warning: {alertsData.by_severity.warning}
            </span>
            <span className="text-netdata-text-muted">Info: {alertsData.by_severity.info}</span>
          </div>
          {alertsData.unreachable_hosts.length > 0 && (
            <div className="text-xs text-netdata-text-dim">
              Unreachable hosts: {alertsData.unreachable_hosts.join(', ')}
            </div>
          )}
        </div>

        <ul className="overflow-y-auto flex-1 space-y-1">
          {sortedAlerts.length === 0 ? (
            <li className="text-center text-netdata-text-muted mt-8">
              <div className="text-4xl mb-2">✓</div>
              <p>No active alerts</p>
            </li>
          ) : (
            sortedAlerts.map((alert) => (
              <li
                key={`${alert.source_host}-${alert.alert_id}`}
                className={`px-2.5 py-2 rounded-lg text-sm ${getSeverityBg(alert.severity)} text-netdata-text-primary`}
              >
                {alert.message} on {alert.source_host}
              </li>
            ))
          )}
        </ul>
      </aside>
    </div>
  );
}
