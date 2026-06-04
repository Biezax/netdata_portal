'use client';

interface TabSwitcherProps {
  activeTab: 'hosts' | 'alerts';
  onTabChange: (tab: 'hosts' | 'alerts') => void;
}

export default function TabSwitcher({ activeTab, onTabChange }: TabSwitcherProps) {
  return (
    <div className="flex w-full gap-1">
      <button
        type="button"
        onClick={() => onTabChange('hosts')}
        className={`flex-1 px-4 py-1.5 rounded-full text-sm transition-all ${
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
        className={`flex-1 px-4 py-1.5 rounded-full text-sm transition-all ${
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
