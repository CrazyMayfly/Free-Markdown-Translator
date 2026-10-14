import { reactive } from "vue";
import { api } from "./api/client";

/** Global backend connectivity state, shared by the shell banner and pages. */
export const connection = reactive({
  checking: true,
  online: false,
  error: null as string | null,
});

export async function checkConnection(): Promise<boolean> {
  connection.checking = true;
  try {
    await api.health();
    connection.online = true;
    connection.error = null;
    return true;
  } catch (error) {
    connection.online = false;
    connection.error = error instanceof Error ? error.message : String(error);
    return false;
  } finally {
    connection.checking = false;
  }
}
