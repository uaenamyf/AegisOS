// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 controllers/index.ts，barrel 导出 interaction/events/routes 控制器

export { interactionController } from "./interaction";
export { eventController } from "./events";
export { routeController, ROUTES } from "./routes";
