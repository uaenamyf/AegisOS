// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 main.tsx，React 根挂载入口

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./DemoApp";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found in index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
