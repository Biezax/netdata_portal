'use client';

interface BrandMarkProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  className?: string;
}

const sizeClasses = {
  sm: {
    mark: 'h-8 w-8',
    title: 'text-sm',
  },
  md: {
    mark: 'h-10 w-10',
    title: 'text-base',
  },
  lg: {
    mark: 'h-12 w-12',
    title: 'text-lg',
  },
};

export default function BrandMark({ size = 'md', showText = true, className = '' }: BrandMarkProps) {
  const classes = sizeClasses[size];

  return (
    <div className={`flex min-w-0 items-center gap-2.5 ${className}`}>
      <div
        className={`${classes.mark} relative flex shrink-0 items-center justify-center rounded-lg border border-netdata-border bg-netdata-dark shadow-sm`}
        aria-hidden="true"
      >
        <svg viewBox="0 0 40 40" className="h-full w-full" role="img">
          <rect x="8" y="22" width="4" height="8" rx="2" fill="#44c442" />
          <rect x="15" y="14" width="4" height="16" rx="2" fill="#8cc63f" />
          <rect x="22" y="9" width="4" height="21" rx="2" fill="#bbf3bb" />
          <rect x="29" y="17" width="4" height="13" rx="2" fill="#ffc107" />
          <path
            d="M10 20.5 17 12.5 24 8.5 31 15.5"
            fill="none"
            stroke="#ffffff"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeOpacity="0.72"
            strokeWidth="2"
          />
          <circle cx="10" cy="20.5" r="2.5" fill="#44c442" stroke="#1f2328" strokeWidth="1.5" />
          <circle cx="17" cy="12.5" r="2.5" fill="#8cc63f" stroke="#1f2328" strokeWidth="1.5" />
          <circle cx="24" cy="8.5" r="2.5" fill="#bbf3bb" stroke="#1f2328" strokeWidth="1.5" />
          <circle cx="31" cy="15.5" r="2.5" fill="#ffc107" stroke="#1f2328" strokeWidth="1.5" />
        </svg>
      </div>
      {showText && (
        <div className="min-w-0">
          <div className={`${classes.title} truncate font-semibold leading-tight text-netdata-text-primary`}>
            Netdata Portal
          </div>
        </div>
      )}
    </div>
  );
}
