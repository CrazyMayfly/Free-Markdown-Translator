import { onBeforeUnmount, ref } from "vue";
import { jobEventsUrl } from "../api/client";

export interface JobEvent {
  seq: number;
  type: string;
  ts: number;
  status?: string;
  error?: string;
  input?: string;
  lang?: string;
  bundle_id?: string;
  done?: number;
  total?: number;
  index?: number;
  bundles?: number;
  usage?: Record<string, number>;
  results?: unknown[];
}

export type JobEventHandler = (event: JobEvent) => void;

/** Subscribe to a job's SSE stream; ends cleanly when the server sends `end`. */
export function useJobEvents(jobId: string, onEvent: JobEventHandler, onEnd?: (status: string) => void) {
  const connected = ref(false);
  let source: EventSource | null = null;
  const handled = new Set<number>();

  const connect = () => {
    source = new EventSource(jobEventsUrl(jobId));
    source.onopen = () => {
      connected.value = true;
    };
    const types = ["status", "pair_start", "progress", "pair_done"];
    for (const type of types) {
      source.addEventListener(type, (raw) => {
        const event = JSON.parse((raw as MessageEvent).data) as JobEvent;
        if (handled.has(event.seq)) return;
        handled.add(event.seq);
        onEvent(event);
      });
    }
    source.addEventListener("end", (raw) => {
      const payload = JSON.parse((raw as MessageEvent).data) as { status: string };
      connected.value = false;
      source?.close();
      source = null;
      onEnd?.(payload.status);
    });
    source.onerror = () => {
      connected.value = false;
      // EventSource auto-reconnects; the server replays from seq 0 which the
      // handled-set deduplicates.
    };
  };

  const close = () => {
    source?.close();
    source = null;
    connected.value = false;
  };

  onBeforeUnmount(close);
  return { connected, connect, close };
}
