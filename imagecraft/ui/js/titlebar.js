// Custom title bar: drag-to-move (frameless window), theme toggle, and the
// minimize / maximize / close buttons. Window operations go through the
// backend bridge (which forwards to pywebview's native window).

import { call } from "./api.js";
import { setState, state } from "./state.js";

let dragging = false;
let startSX = 0;
let startSY = 0;
let startWX = 0;
let startWY = 0;

export function initTitlebar() {
  const region = document.getElementById("drag-region");

  // --- Window dragging ----------------------------------------------------
  region.addEventListener("mousedown", (e) => {
    if (e.button !== 0 || state.compareOn) return;
    dragging = true;
    startSX = e.screenX;
    startSY = e.screenY;
    startWX = window.screenX;
    startWY = window.screenY;
    e.preventDefault();
  });

  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    call("move_window", startWX + (e.screenX - startSX), startWY + (e.screenY - startSY)).catch(() => {});
  });

  window.addEventListener("mouseup", () => {
    dragging = false;
  });

  // --- Window control buttons ----------------------------------------------
  document.getElementById("btn-min").addEventListener("click", () =>
    call("minimize_window").catch(() => {}),
  );

  const maxBtn = document.getElementById("btn-max");
  maxBtn.addEventListener("click", () => {
    const willMaximize = maxBtn.textContent !== "❐";
    call("toggle_maximize").catch(() => {});
    maxBtn.textContent = willMaximize ? "❐" : "▢";
  });

  document.getElementById("btn-close").addEventListener("click", () =>
    call("close_window").catch(() => {}),
  );

  // --- Theme toggle ---------------------------------------------------------
  document.getElementById("btn-theme").addEventListener("click", () => {
    const next = state.theme === "dark" ? "light" : "dark";
    setTheme(next);
    call("set_config", "theme", next).catch(() => {});
  });
}

export function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  setState({ theme });
}
