import { describe, it, expect } from 'vitest';

import {
  HOST_UNREACHABLE_STATUS,
  deriveNotificationStatus,
  isKnownUnreachable,
  type HostNotificationStatus,
} from './notificationStatus';

const reachable = { status: { reachable: true, last_check: '2026-06-10T00:00:00Z' } };
const unreachable = { status: { reachable: false, last_check: '2026-06-10T00:00:00Z' } };
const unchecked = { status: { reachable: false, last_check: null } };

const fetched: HostNotificationStatus = { state: 'enabled', message: null };

describe('isKnownUnreachable', () => {
  it('is true only when a host has been checked and is not reachable', () => {
    expect(isKnownUnreachable(unreachable)).toBe(true);
    expect(isKnownUnreachable(reachable)).toBe(false);
    expect(isKnownUnreachable(unchecked)).toBe(false);
  });
});

describe('deriveNotificationStatus', () => {
  it('overrides a down host with the unreachable status', () => {
    expect(deriveNotificationStatus(unreachable, fetched)).toBe(HOST_UNREACHABLE_STATUS);
  });

  it('passes the fetched status through for a reachable host', () => {
    expect(deriveNotificationStatus(reachable, fetched)).toBe(fetched);
  });

  it('does not override a host that has never been checked', () => {
    expect(deriveNotificationStatus(unchecked, fetched)).toBe(fetched);
  });

  it('returns undefined when a reachable host has no fetched status yet', () => {
    expect(deriveNotificationStatus(reachable, undefined)).toBeUndefined();
  });
});
