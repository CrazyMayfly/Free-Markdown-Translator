<script setup lang="ts">
import { confirmState, settleConfirm } from "../confirm";

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") settleConfirm(false);
}
</script>

<template>
  <dialog class="modal" :class="{ 'modal-open': confirmState.open }" @keydown="onKeydown">
    <div class="modal-box max-w-sm">
      <h3 class="text-base font-bold">请确认</h3>
      <p class="mt-2 text-sm text-base-content/70">{{ confirmState.message }}</p>
      <div class="modal-action">
        <button class="btn btn-ghost btn-sm" @click="settleConfirm(false)">取消</button>
        <button
          class="btn btn-sm"
          :class="confirmState.danger ? 'btn-error' : 'btn-primary'"
          @click="settleConfirm(true)"
        >
          {{ confirmState.confirmLabel }}
        </button>
      </div>
    </div>
    <div class="modal-backdrop" @click="settleConfirm(false)"></div>
  </dialog>
</template>
