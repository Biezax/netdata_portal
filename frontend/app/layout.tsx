import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Netdata Multi-Instance Aggregator',
  description: 'Monitor multiple Netdata instances from a unified interface',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-netdata-bg">
        {children}
      </body>
    </html>
  );
}
