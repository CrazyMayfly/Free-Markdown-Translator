import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import { setApiBase } from "./api/client";
import router from "./router";
import { resolveApiBase } from "./tauri";
import "./style.css";

async function bootstrap() {
  setApiBase(await resolveApiBase());
  createApp(App).use(createPinia()).use(router).mount("#app");
}

void bootstrap();
