// Desktop notifications with graceful degradation: the Tauri notification
// plugin when packaged, the Web Notification API in plain browser dev mode.
import { isTauri } from "./tauri";

let webPermission: NotificationPermission | "unknown" = "unknown";

export async function ensureNotifyPermission(): Promise<boolean> {
  try {
    if (isTauri()) {
      const plugin = await import("@tauri-apps/plugin-notification");
      let granted = await plugin.isPermissionGranted();
      if (!granted) granted = (await plugin.requestPermission()) === "granted";
      return granted;
    }
    if (webPermission === "unknown") {
      webPermission = await Notification.requestPermission();
    }
    return webPermission === "granted";
  } catch {
    return false;
  }
}

export async function notifyApp(title: string, body: string): Promise<void> {
  try {
    if (isTauri()) {
      const plugin = await import("@tauri-apps/plugin-notification");
      if (await plugin.isPermissionGranted()) {
        plugin.sendNotification({ title, body });
      }
      return;
    }
    if (webPermission === "granted") {
      new Notification(title, { body });
    }
  } catch {
    /* best effort — never break the app over a notification */
  }
}
