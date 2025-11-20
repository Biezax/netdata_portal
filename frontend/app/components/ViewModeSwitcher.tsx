'use client';

type ViewMode = 'dashboard' | 'alerts';

interface ViewModeSwitcherProps {
  currentMode: ViewMode;
  onModeChange: (mode: ViewMode) => void;
}

export default function ViewModeSwitcher({ currentMode, onModeChange }: ViewModeSwitcherProps) {
  return (
    <div className="flex gap-2 bg-netdata-dark p-1 rounded-lg">
      <button
        onClick={() => onModeChange('dashboard')}
        className={`px-4 py-2 rounded transition-colors ${
          currentMode === 'dashboard'
            ? 'bg-netdata-accent text-white'
            : 'text-gray-400 hover:text-white hover:bg-gray-800'
        }`}
      >
        Dashboard
      </button>
      <button
        onClick={() => onModeChange('alerts')}
        className={`px-4 py-2 rounded transition-colors ${
          currentMode === 'alerts'
            ? 'bg-netdata-accent text-white'
            : 'text-gray-400 hover:text-white hover:bg-gray-800'
        }`}
      >
        Alerts
      </button>
    </div>
  );
}
