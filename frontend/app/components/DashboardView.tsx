'use client';

interface DashboardViewProps {
  hostname: string;
}

export default function DashboardView({ hostname }: DashboardViewProps) {
  const proxyUrl = `/api/proxy/${hostname}/v3`;

  return (
    <section className="flex-1 rounded-2xl border border-netdata-border overflow-hidden bg-netdata-bg">
      <iframe
        src={proxyUrl}
        className="w-full h-full border-0"
        title={`Netdata dashboard for ${hostname}`}
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
        allow="fullscreen"
      />
    </section>
  );
}
