import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/submit" },
    { path: "/submit", name: "submit", component: () => import("./views/SubmitView.vue") },
    { path: "/run/:id", name: "run", component: () => import("./views/RunView.vue") },
    { path: "/result/:id", name: "result", component: () => import("./views/ResultView.vue") },
    { path: "/config", name: "config", component: () => import("./views/ConfigView.vue") },
  ],
});

export default router;
