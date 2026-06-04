'use client';

import { useState } from 'react';
import { Bell, BellOff, CircleHelp, LoaderCircle, LogOut, Menu, X } from 'lucide-react';
import TabSwitcher from './TabSwitcher';

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

interface HostsSidebarProps {
  hosts: Host[];
  selectedHost: string | null;
  onSelectHost: (hostname: string) => void;
  viewMode: ViewMode;
  onViewModeChange: (viewMode: ViewMode) => void;
  notificationStatuses: Record<string, HostNotificationStatus>;
  notificationBusy: Record<string, boolean>;
  onToggleNotifications: (hostname: string) => void;
  user: string | null;
  onLogout: () => void;
}

type ViewMode = 'hosts' | 'alerts';
type NotificationState = 'enabled' | 'silenced' | 'partial' | 'disabled' | 'unknown' | 'unavailable';

interface HostNotificationStatus {
  state: NotificationState;
  message: string | null;
  retryable?: boolean;
}

interface TooltipState {
  label: string;
  left: number;
  top: number;
}

export default function HostsSidebar({
  hosts,
  selectedHost,
  onSelectHost,
  viewMode,
  onViewModeChange,
  notificationStatuses,
  notificationBusy,
  onToggleNotifications,
  user,
  onLogout,
}: HostsSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);

  const filteredHosts = hosts.filter((host) =>
    host.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectHost = (hostname: string) => {
    onSelectHost(hostname);
    setMobileOpen(false);
    setTooltip(null);
  };

  const changeViewMode = (nextViewMode: ViewMode) => {
    onViewModeChange(nextViewMode);
    setMobileOpen(false);
    setTooltip(null);
  };

  return (
    <>
      {!mobileOpen && (
        <button
          type="button"
          aria-label="Open navigation"
          onClick={() => setMobileOpen(true)}
          className="fixed left-3 top-3 z-50 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-netdata-border bg-netdata-bg/90 text-netdata-text-primary shadow-lg backdrop-blur-md md:hidden"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
      )}

      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={() => {
            setMobileOpen(false);
            setTooltip(null);
          }}
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
        />
      )}

      <aside className={`group/sidebar fixed inset-y-0 left-0 z-40 flex w-[320px] flex-col border-r border-netdata-border bg-netdata-bg/82 p-3 shadow-2xl backdrop-blur-md transition-transform duration-200 ease-out ${
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      } ${searchFocused ? 'md:translate-x-0' : 'md:-translate-x-[312px] md:hover:translate-x-0'}`}>
        <div className="absolute right-1 top-1/2 hidden h-14 w-1 -translate-y-1/2 rounded-full bg-netdata-accent/70 group-hover/sidebar:bg-netdata-accent md:block" />
        <div className="mb-3 flex items-center gap-2">
          <div className="min-w-0 flex-1 rounded-full border border-netdata-border bg-netdata-panel-bg/70 p-1">
            <TabSwitcher activeTab={viewMode} onTabChange={changeViewMode} />
          </div>
          <button
            type="button"
            aria-label="Close navigation"
            onClick={() => {
              setMobileOpen(false);
              setTooltip(null);
            }}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-netdata-border-dark text-netdata-text-muted hover:text-netdata-text-primary md:hidden"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <div className="mb-2 text-sm font-medium text-netdata-text-muted">Hosts</div>

        <div className="mb-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            placeholder="Filter by hostname"
            className="w-full px-2.5 py-1.5 rounded-full border border-netdata-border-dark bg-netdata-bg text-netdata-text-primary text-sm outline-none placeholder:text-netdata-text-dim"
          />
        </div>

        <ul className="mt-1 min-h-0 flex-1 space-y-0.5 overflow-y-auto pr-3">
          {filteredHosts.map((host) => {
            const notificationStatus = notificationStatuses[host.name] || {
              state: 'unknown' as const,
              message: 'Loading notification status',
            };
            const busy = Boolean(notificationBusy[host.name]);
            const control = getNotificationControl(notificationStatus, busy);
            const criticalCount = host.status.critical_count ?? 0;
            const warningCount = host.status.warning_count ?? 0;
            const hostNameColor = !host.status.reachable
              ? 'text-netdata-critical'
              : selectedHost === host.name
                ? 'text-netdata-accent-light'
                : 'text-netdata-text-primary';

            return (
              <li
                key={host.name}
                onClick={() => selectHost(host.name)}
                className={`px-2.5 py-2 rounded-lg text-sm cursor-pointer flex items-center gap-2 transition-all ${
                  selectedHost === host.name
                    ? 'bg-netdata-accent-dim'
                    : 'hover:bg-netdata-panel-bg'
                }`}
              >
                <span className={`min-w-0 flex-1 truncate ${hostNameColor}`}>{host.name}</span>
                <span className="flex-shrink-0 tabular-nums text-xs font-semibold" aria-label={`${criticalCount} critical, ${warningCount} warnings`}>
                  <span className="text-netdata-critical">{criticalCount}</span>
                  <span className="px-0.5 text-netdata-text-dim">/</span>
                  <span className="text-netdata-warning">{warningCount}</span>
                </span>
                <span className="flex-shrink-0">
                  <button
                    type="button"
                    title={control.label}
                    aria-label={`${control.label} for ${host.name}`}
                    disabled={control.disabled}
                    onMouseEnter={(event) => showTooltip(event.currentTarget, control.label, setTooltip)}
                    onMouseLeave={() => setTooltip(null)}
                    onFocus={(event) => showTooltip(event.currentTarget, control.label, setTooltip)}
                    onBlur={() => setTooltip(null)}
                    onClick={(event) => {
                      event.stopPropagation();
                      if (!control.disabled) {
                        onToggleNotifications(host.name);
                      }
                    }}
                    className={`h-7 w-7 rounded-md border border-netdata-border-dark inline-flex items-center justify-center transition-colors ${control.className}`}
                  >
                    <control.Icon className={busy ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} aria-hidden="true" />
                  </button>
                </span>
              </li>
            );
          })}
        </ul>

        {user && (
          <div className="mt-3 flex items-center gap-2 border-t border-netdata-border pt-3">
            <span className="min-w-0 flex-1 truncate text-sm text-netdata-text-secondary">{user}</span>
            <button
              type="button"
              title="Logout"
              aria-label="Logout"
              onClick={onLogout}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-netdata-border-dark text-netdata-text-muted hover:text-netdata-text-primary"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        )}
      </aside>

      {tooltip && (
        <div
          className="pointer-events-none fixed z-50 -translate-y-1/2 whitespace-nowrap rounded-md border border-netdata-border-dark bg-netdata-dark px-2 py-1 text-xs text-netdata-text-secondary shadow-lg"
          style={{ left: tooltip.left, top: tooltip.top }}
        >
          {tooltip.label}
        </div>
      )}
    </>
  );
}

function showTooltip(
  element: HTMLElement,
  label: string,
  setTooltip: (tooltip: TooltipState | null) => void
) {
  const rect = element.getBoundingClientRect();
  setTooltip({
    label,
    left: rect.right + 8,
    top: rect.top + rect.height / 2,
  });
}

function getNotificationControl(status: HostNotificationStatus, busy: boolean) {
  if (busy) {
    return {
      Icon: LoaderCircle,
      label: 'Updating notifications',
      disabled: true,
      className: 'text-netdata-text-muted cursor-wait',
    };
  }

  if (status.state === 'enabled') {
    return {
      Icon: BellOff,
      label: 'Silence notifications',
      disabled: false,
      className: 'text-netdata-warning hover:border-netdata-warning hover:bg-netdata-alert-warning',
    };
  }

  if (status.state === 'silenced' || status.state === 'partial' || status.state === 'disabled') {
    return {
      Icon: Bell,
      label: 'Enable notifications',
      disabled: false,
      className: 'text-netdata-accent-light hover:border-netdata-accent hover:bg-netdata-accent-dim',
    };
  }

  return {
    Icon: CircleHelp,
    label: status.message || 'Notification status unavailable',
    disabled: true,
    className: 'text-netdata-text-dim opacity-60 cursor-not-allowed',
  };
}
