'use client';

import { useCallback, useRef } from 'react';

interface DashboardViewProps {
  hostname: string;
}

export default function DashboardView({ hostname }: DashboardViewProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const proxyRoot = `/api/proxy/${encodeURIComponent(hostname)}/`;
  const proxyUrl = `${proxyRoot}v3/`;
  const resetExternalNavigation = useCallback(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    try {
      const location = iframe.contentWindow?.location;
      if (!location) return;

      if (location.origin !== window.location.origin || !location.pathname.startsWith(proxyRoot)) {
        iframe.src = proxyUrl;
      }
    } catch {
      iframe.src = proxyUrl;
    }
  }, [proxyRoot, proxyUrl]);

  return (
    <section className="absolute inset-0 bg-netdata-darker">
      <iframe
        ref={iframeRef}
        src={proxyUrl}
        className="h-full w-full border-0"
        title={`Netdata dashboard for ${hostname}`}
        sandbox="allow-scripts allow-same-origin allow-forms allow-modals"
        allow="fullscreen"
        onLoad={resetExternalNavigation}
      />
    </section>
  );
}
