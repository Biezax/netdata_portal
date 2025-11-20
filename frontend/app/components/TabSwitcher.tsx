'use client';

interface TabSwitcherProps {
  activeTab: 'hosts' | 'alerts';
  onTabChange: (tab: 'hosts' | 'alerts') => void;
}

export default function TabSwitcher({ activeTab, onTabChange }: TabSwitcherProps) {
  return (
    <div className="inline-flex rounded-full bg-netdata-bg border border-netdata-border p-0.5 gap-0.5">
      <button
        type="button"
        onClick={() => onTabChange('hosts')}
        className={`px-4 py-1.5 rounded-full text-sm transition-all ${
          activeTab === 'hosts'
            ? 'bg-netdata-accent text-netdata-bg font-medium'
            : 'bg-transparent text-netdata-text-muted hover:text-netdata-text-primary'
        }`}
      >
        Hosts
      </button>
      <button
        type="button"
        onClick={() => onTabChange('alerts')}
        className={`px-4 py-1.5 rounded-full text-sm transition-all ${
          activeTab === 'alerts'
            ? 'bg-netdata-accent text-netdata-bg font-medium'
            : 'bg-transparent text-netdata-text-muted hover:text-netdata-text-primary'
        }`}
      >
        Alerts
      </button>
    </div>
  );
}
