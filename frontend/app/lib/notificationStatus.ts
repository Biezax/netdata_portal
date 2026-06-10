export type NotificationState =
  | 'enabled'
  | 'silenced'
  | 'partial'
  | 'disabled'
  | 'unknown'
  | 'unavailable';

export interface HostNotificationStatus {
  state: NotificationState;
  message: string | null;
  retryable?: boolean;
}

interface HostReachability {
  status: {
    reachable: boolean;
    last_check: string | null;
  };
}

export const HOST_UNREACHABLE_STATUS: HostNotificationStatus = {
  state: 'unavailable',
  message: 'Host is unreachable',
  retryable: true,
};

export function isKnownUnreachable(host: HostReachability): boolean {
  return host.status.last_check !== null && !host.status.reachable;
}

// A down host's bell is derived from /api/hosts (the same source as the row color)
// rather than its own notification fetch, so the two can never disagree and no
// client-side refresh trigger is needed when reachability flips.
export function deriveNotificationStatus(
  host: HostReachability,
  fetched: HostNotificationStatus | undefined
): HostNotificationStatus | undefined {
  return isKnownUnreachable(host) ? HOST_UNREACHABLE_STATUS : fetched;
}
