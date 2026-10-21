import { reactive } from "vue";
import { api } from "./api/client";

/** Global backend connectivity state, shared by the shell banner and pages. */
export const connection = reactive({
  checking: true,
  online: false,
  error: null as string | null,
  /** Capabilities advertised by the sidecar via /api/health. */
  features: [] as string[],
});

/** True when the sidecar build supports a capability (e.g. "stage-events"). */
export function supportsFeature(name: string): boolean {
  return connection.features.includes(name);
}

export async function checkConnection(): Promise<boolean> {
  connection.checking = true;
  try {
    const health = await api.health();
    connection.online = true;
    connection.error = null;
    connection.features = health.features ?? [];
    return true;
  } catch (error) {
    connection.online = false;
    connection.features = [];
    connection.error = error instanceof Error ? error.message : String(error);
    return false;
  } finally {
    connection.checking = false;
  }
}
