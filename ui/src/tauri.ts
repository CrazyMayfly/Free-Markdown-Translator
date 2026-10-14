// Tauri integration: sidecar handshake and native file drop.
// In the browser these degrade to no-ops.

export interface ConnectionResult {
  base: string;
  error: string | null;
}

export async function resolveApiBase(): Promise<ConnectionResult> {
  if (window.__MDTX_API_BASE__) {
    return { base: window.__MDTX_API_BASE__, error: null };
  }
  const tauri = (window as Record<string, unknown>).__TAURI_INTERNALS__;
  if (!tauri) {
    return { base: "", error: null };
  }
  const { invoke } = await import("@tauri-apps/api/core");
  const { listen } = await import("@tauri-apps/api/event");

  // Race-free initial query: the shell stores the port once the sidecar
  // accepts connections, so a command issued at any later moment succeeds
  // even if the api-ready event fired before this page started listening.
  try {
    const port = (await invoke("api_ready_state")) as number | null;
    if (typeof port === "number") {
      return { base: `http://127.0.0.1:${port}`, error: null };
    }
  } catch {
    /* command unavailable (old shell?) — fall through to events */
  }

  return new Promise<ConnectionResult>((resolve) => {
    let settled = false;
    const finish = (result: ConnectionResult) => {
      if (settled) return;
      settled = true;
      readyUnlisten.then((fn) => fn());
      errorUnlisten.then((fn) => fn());
      resolve(result);
    };
    const readyUnlisten = listen<number>("api-ready", (event) => {
      finish({ base: `http://127.0.0.1:${event.payload}`, error: null });
    });
    const errorUnlisten = listen<string>("api-error", (event) => {
      finish({ base: "", error: String(event.payload) });
    });
    // The sidecar may legitimately take a while on first launch (binary
    // extraction, Gatekeeper scan); give it generous time before failing.
    setTimeout(() => finish({ base: "", error: "后端服务启动超时，请重启应用；若反复出现请查看应用日志" }), 90000);
  });
}

/** Absolute paths of files/folders dropped onto the window (Tauri only). */
export async function onNativeFileDrop(callback: (paths: string[]) => void): Promise<() => void> {
  const tauri = (window as Record<string, unknown>).__TAURI_INTERNALS__;
  if (!tauri) {
    return () => undefined;
  }
  const { getCurrentWebviewWindow } = await import("@tauri-apps/api/webviewWindow");
  const webview = getCurrentWebviewWindow();
  const unlisten = await webview.onDragDropEvent((event) => {
    if (event.payload.type === "drop") {
      const paths = (event.payload.paths ?? []).filter((p) => /\.(md|markdown)$/i.test(p) || p.split("/").pop()?.includes(".") === false);
      if (paths.length) callback(paths);
    }
  });
  return unlisten;
}

export function isTauri(): boolean {
  return Boolean((window as Record<string, unknown>).__TAURI_INTERNALS__);
}
