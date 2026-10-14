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
  const { listen } = await import("@tauri-apps/api/event");
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
    // Fallback: never block the UI forever if the sidecar is slow to emit.
    setTimeout(() => finish({ base: "", error: "等待后端服务启动超时" }), 35000);
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
