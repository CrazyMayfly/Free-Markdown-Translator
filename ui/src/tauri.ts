// Resolves the sidecar API base URL inside the Tauri shell.
// In the browser (dev via vite proxy) this resolves to "" immediately.

export async function resolveApiBase(): Promise<string> {
  if (window.__MDTX_API_BASE__) {
    return window.__MDTX_API_BASE__;
  }
  const tauri = (window as Record<string, unknown>).__TAURI_INTERNALS__;
  if (!tauri) {
    return "";
  }
  const { listen } = await import("@tauri-apps/api/event");
  return new Promise<string>((resolve) => {
    let settled = false;
    const finish = (base: string) => {
      if (settled) return;
      settled = true;
      unlisten.then((fn) => fn());
      resolve(base);
    };
    const unlisten = listen<number>("api-ready", (event) => {
      finish(`http://127.0.0.1:${event.payload}`);
    });
    listen<number>("api-error", () => {
      finish("");
    });
    // Fallback: never block the UI forever if the sidecar is slow to emit.
    setTimeout(() => finish(""), 10000);
  });
}
