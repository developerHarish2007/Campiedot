// Centralized configuration for CampusOps 3D Digital Twin and Dashboard URLs
export const DASHBOARD_URL: string =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_DASHBOARD_URL) || 'http://localhost:5173';

export const TWIN_URL: string =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_TWIN_URL) || 'http://localhost:5174';

/**
 * Opens the CampusOps Dashboard in a single persistent named tab.
 * Pings the URL first (1.5s timeout). If offline, shows a toast notification
 * and does not open a blank tab. Always opens the home/default route.
 */
export async function openDashboard(onToast?: (message: string) => void): Promise<boolean> {
  const targetUrl = new URL(DASHBOARD_URL).origin + '/';

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 1500);

    await fetch(targetUrl, {
      mode: 'no-cors',
      signal: controller.signal,
    });
    clearTimeout(timer);

    window.open(targetUrl, 'campusops-dashboard');
    return true;
  } catch (err) {
    const msg = 'Dashboard is not running. Start both with: npm run dev:all';
    if (onToast) {
      onToast(msg);
    } else if (typeof window !== 'undefined') {
      alert(msg);
    }
    return false;
  }
}

/**
 * Navigates back from dashboard to 3D Twin using persistent named tab.
 */
export function openTwinTab(): void {
  const targetUrl = new URL(TWIN_URL).origin + '/';
  window.open(targetUrl, 'campusops-twin');
}
