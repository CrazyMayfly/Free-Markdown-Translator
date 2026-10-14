import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import { setApiBase } from "./api/client";
import { checkConnection, connection } from "./connection";
import router from "./router";
import { resolveApiBase } from "./tauri";
import "./style.css";

async function bootstrap() {
  const result = await resolveApiBase();
  setApiBase(result.base);
  connection.checking = false;
  connection.error = result.error;
  if (!result.error) {
    void checkConnection();
  } else {
    connection.online = false;
  }
  createApp(App).use(createPinia()).use(router).mount("#app");
}

void bootstrap();
