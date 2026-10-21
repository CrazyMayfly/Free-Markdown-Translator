// Promise-based confirm dialog. window.confirm does not work inside the
// Tauri WKWebView (it silently returns false), which made destructive buttons
// dead and the config leave-guard permanently block navigation. This module
// drives a single daisyUI modal mounted once in App.vue.
import { ref } from "vue";

interface ConfirmState {
  open: boolean;
  message: string;
  confirmLabel: string;
  danger: boolean;
}

export const confirmState = ref<ConfirmState>({
  open: false,
  message: "",
  confirmLabel: "确定",
  danger: false,
});

let resolver: ((value: boolean) => void) | null = null;

export function confirmAction(message: string, options?: { confirmLabel?: string; danger?: boolean }): Promise<boolean> {
  // A second request while one is open resolves the previous as cancelled.
  if (resolver) resolver(false);
  return new Promise<boolean>((resolve) => {
    resolver = resolve;
    confirmState.value = {
      open: true,
      message,
      confirmLabel: options?.confirmLabel ?? "确定",
      danger: options?.danger ?? true,
    };
  });
}

export function settleConfirm(value: boolean): void {
  confirmState.value.open = false;
  resolver?.(value);
  resolver = null;
}
