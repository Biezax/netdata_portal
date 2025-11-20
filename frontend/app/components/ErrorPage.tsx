'use client';

interface ErrorPageProps {
  message: string;
  details?: string;
}

export default function ErrorPage({ message, details }: ErrorPageProps) {
  return (
    <div className="flex-1 flex items-center justify-center bg-netdata-darker">
      <div className="max-w-md text-center p-8">
        <div className="text-6xl mb-4">❌</div>
        <h2 className="text-2xl font-bold text-netdata-critical mb-4">{message}</h2>
        {details && <p className="text-gray-400">{details}</p>}
      </div>
    </div>
  );
}
