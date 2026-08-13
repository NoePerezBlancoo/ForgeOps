import type { User } from "@/lib/types";

interface CachedIdentity {
  user: User;
  expiresAt: string;
}

const STORAGE_KEY = "forgeops.offline.identity";
const OFFLINE_IDENTITY_HOURS = 24;

export function saveOfflineIdentity(user: User): void {
  const expiresAt = new Date(Date.now() + OFFLINE_IDENTITY_HOURS * 60 * 60 * 1000).toISOString();
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ user, expiresAt } satisfies CachedIdentity));
}

export function loadOfflineIdentity(): User | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const cached = JSON.parse(raw) as CachedIdentity;
    if (!cached.user?.id || !cached.user.company_id || Date.parse(cached.expiresAt) <= Date.now()) {
      clearOfflineIdentity();
      return null;
    }
    return cached.user;
  } catch {
    clearOfflineIdentity();
    return null;
  }
}

export function clearOfflineIdentity(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}
