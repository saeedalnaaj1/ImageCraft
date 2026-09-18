// Application bootstrap: wires the title bar, toolbar, sidebar, status bar,
// shortcuts, backend events, and the preview pipeline together.

import { call, isPyWebView, onBackend, onReady } from "./api.js";
import { applyBackendState, setState, state, setEditParams } from "./state.js";
import { toast, ok, err } from "./toast.js";
import { initProgress } from "./progress.js";
import { initTitlebar, setTheme } from "./titlebar.js";
import { initSidebar, setActive as setSidebarActive, toggleCollapsed, applyLayout, configurePanelHooks } from "./sidebar.js";

import { Viewer } from "./viewer.js";
import { initCompare, showCompare, hideCompare } from "./compare.js";
import { showModal } from "./modal.js";
import { showTutorial } from "./tutorial.js";

const viewer = new Viewer(document.getElementById("viewer-canvas"));
viewer.onChange = () => updateZoomReadout();

let previewTimer = 0;

// ---------------------------------------------------------------------------
// Preview pipeline
// ---------------------------------------------------------------------------


async function refreshPreview() {
  const hasImage = state.current != null;
  const empty = document.getElementById("empty-state");
  empty.hidden = hasImage;
  const tools = document.getElementById("viewer-tools");
  if (tools) tools.hidden = !hasImage;
  if (!hasImage) {
    viewer.clear();
    return;
  }
  window.clearTimeout(previewTimer);
  previewTimer = window.setTimeout(async () => {
    try {
      const tool = state.activeTool;
      const params = state.editParams[tool];
      let res;
      if (params && Object.keys(params).length > 0) {
        res = await call("preview", tool, params);
      } else {
        res = await call("get_preview");
      }
      if (res && res.dataUrl) {
        await viewer.setImage(res.dataUrl, { preserveView: false });
        updateZoomReadout();
      }
    } catch (e) {
      // Transient failures (e.g. invalid crop) shouldn't clear the canvas.
      console.warn("preview failed:", e);
    }
  }, 90);
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

async function openImage() {
  try {
    const payload = await call("open_image_dialog");
    if (payload.cancelled) return;
    applyBackendState(payload);
    afterState();
    ok("Image loaded", state.current ? state.current.name : "");
  } catch (e) {
    err("Open failed", e.message);
  }
}

async function openFolder() {
  try {
    const payload = await call("open_folder_dialog");
    if (payload.cancelled) return;
    applyBackendState(payload);
    afterState();
    ok("Folder loaded", `${state.images.length} images`);
  } catch (e) {
    err("Open folder failed", e.message);
  }
}

async function undo() {
  try {
    applyBackendState(await call("undo"), { resetControls: true });
    afterState();
  } catch (e) {
    err("Undo failed", e.message);
  }
}

async function redo() {
  try {
    applyBackendState(await call("redo"), { resetControls: true });
    afterState();
  } catch (e) {
    err("Redo failed", e.message);
  }
}

async function resetCurrent() {
  try {
    applyBackendState(await call("reset_current"), { resetControls: true });
    afterState();
    ok("Reset", "Current image reverted to original");
  } catch (e) {
    err("Reset failed", e.message);
  }
}

async function resetAll() {
  try {
    applyBackendState(await call("reset_all"), { resetControls: true });
    afterState();
    ok("Reset all", "All images reverted to original");
  } catch (e) {
    err("Reset failed", e.message);
  }
}

async function saveImage() {
  try {
    const res = await call("save_image");
    if (res.ok) ok("Saved", state.current ? state.current.name : "");
    else err("Save", res.message || "No image to save");
  } catch (e) {
    err("Save failed", e.message);
  }
}

async function saveModified() {
  try {
    const res = await call("save_all");
    if (res.ok) ok("Saved modified", `${res.saved} image(s) saved`);
    else err("Save modified", res.message || "No modified images");
  } catch (e) {
    err("Save modified failed", e.message);
  }
}

async function saveSession() {
  try {
    const res = await call("save_session");
    if (res.ok) ok("Saved all", `${res.saved} of ${res.total} image(s) saved`);
    else err("Save all", res.message || "No images to save");
  } catch (e) {
    err("Save all failed", e.message);
  }
}

function navigate(delta) {
  if (state.images.length === 0) return;
  call("navigate", delta)
    .then((payload) => {
      applyBackendState(payload);
      afterState();
    })
    .catch((e) => err("Navigate failed", e.message));
}

// ---------------------------------------------------------------------------
// Toolbar / UI wiring
// ---------------------------------------------------------------------------

function byId(id) {
  return document.getElementById(id);
}

function updateZoomReadout() {
  const el = byId("zoom-readout");
  if (el) el.innerHTML = `<span class="val">${viewer.zoomPercent()}%</span>`;
  const el2 = byId("viewer-zoom-readout");
  if (el2) el2.innerHTML = `<span class="val">${viewer.zoomPercent()}%</span>`;
}

function updateStatusBar() {
  byId("st-state").textContent = state.busy ? "Working…" : "Ready";
  const dim = byId("st-dimensions");
  if (state.current) {
    dim.textContent = `${state.current.w} × ${state.current.h}`;
  } else {
    dim.textContent = "";
  }
  const pos = byId("st-position");
  if (state.images.length > 0) {
    pos.innerHTML = `<b>${state.currentIndex + 1}</b> / ${state.images.length}`;
  } else {
    pos.innerHTML = "";
  }
  byId("tb-undo").disabled = !state.history.canUndo;
  byId("tb-redo").disabled = !state.history.canRedo;
  const canSave = state.current != null && state.current.modified;
  byId("tb-save").disabled = !canSave;
  byId("tb-save-all").disabled = !state.images.some((i) => i.modified);
  byId("tb-save-session").disabled = state.images.length === 0;
  const canCompare = canSave;
  byId("tb-compare").disabled = !canCompare;
  const vzCompare = byId("vz-compare");
  if (vzCompare) vzCompare.disabled = !canCompare;
  updateNavArrows();
}

let navTimer = 0;
function updateNavArrows() {
  const el = document.getElementById("nav-arrows");
  if (!el) return;
  const show = state.images.length > 1 && !state.compareOn;
  el.hidden = !show;
  const prev = document.getElementById("nav-prev");
  const next = document.getElementById("nav-next");
  if (prev) prev.disabled = state.currentIndex <= 0;
  if (next) next.disabled = state.currentIndex >= state.images.length - 1;
}
function flashNavArrows() {
  const el = document.getElementById("nav-arrows");
  if (!el || el.hidden) return;
  el.querySelectorAll("button").forEach(b => b.style.opacity = "1");
  clearTimeout(navTimer);
  navTimer = setTimeout(() => {
    el.querySelectorAll("button").forEach(b => b.style.opacity = "");
  }, 5000);
}

function afterState() {
  updateStatusBar();
  if (state.compareOn) {
    showCompare();
  } else {
    refreshPreview();
  }
}

async function showAboutModal() {
  let info = { name: "ImageCraft", version: "2.0.0", author: "" };
  let caps = {
    cv_version: "",
    opencl: false,
    opencl_in_use: false,
    cores: 1,
    threads: 1,
    cpu_name: "Unknown CPU",
    gpu: null,
    performance_mode: "medium",
    preview_max: 0,
    backend: "CPU only",
  };
  try {
    if (isPyWebView()) {
      [info, caps] = await Promise.all([call("get_app_info"), call("get_capabilities")]);
    }
  } catch (_) { /* use defaults */ }

  const gpu = caps.gpu;
  const gpuLine = gpu
    ? `${gpu.name} — ${gpu.vendor} · OpenCL ${gpu.version || "?"} · driver ${gpu.driver || "?"}`
    : "No OpenCL device detected";
  const cpuLine = `${caps.cpu_name || "Unknown CPU"} — ${caps.cores} core(s)`;
  const modeLabel = caps.performance_mode === "low" ? "Low" : "High";
  const activeEngine = caps.opencl_in_use ? "GPU (OpenCL) + CPU" : "CPU only";
  const threadsLine = `${caps.threads} thread(s) · preview up to ${caps.preview_max || "—"} px`;

  const hwRow = (label, value) =>
    `<p style="margin:0 0 6px;"><span style="display:inline-block;min-width:84px;color:var(--text-3);">${label}</span>${value}</p>`;

  const content = document.createElement("div");
  content.innerHTML = `
    <p style="font-size:var(--fs-l);font-weight:600;margin:0 0 4px;">${info.name} <span style="color:var(--text-3);font-weight:400;">v${info.version}</span></p>
    <p style="color:var(--text-3);margin:0 0 16px;">by ${info.author || "Unknown"}</p>

    <h3 style="margin:0 0 8px;font-size:var(--fs-s);text-transform:uppercase;color:var(--text-3);">Performance Profiles</h3>

    <div class="profile-card${caps.performance_mode === "medium" ? " profile-card--active" : ""}">
      <strong>High</strong> <span style="color:var(--ok);font-size:var(--fs-xs);">Recommended${caps.performance_mode === "medium" ? " · Active" : ""}</span>
      <p style="margin:2px 0 0;font-size:var(--fs-xs);color:var(--text-3);">Uses the GPU via OpenCL plus all CPU cores. Full preview resolution (1920 px). Best for most users.</p>
    </div>
    <div class="profile-card" style="margin-top:8px;${caps.performance_mode === "low" ? "border-left-color:var(--ok);" : ""}">
      <strong>Low</strong>${caps.performance_mode === "low" ? ' <span style="color:var(--ok);font-size:var(--fs-xs);">Active</span>' : ""}
      <p style="margin:2px 0 0;font-size:var(--fs-xs);color:var(--text-3);">CPU-only, single thread. Reduced preview resolution (720 px). Use on machines without a dedicated GPU.</p>
    </div>

    <h3 style="margin:16px 0 8px;font-size:var(--fs-s);text-transform:uppercase;color:var(--text-3);">Hardware</h3>
    ${hwRow("CPU", cpuLine)}
    ${hwRow("GPU", gpuLine)}
    ${hwRow("Active", `${activeEngine} · profile <strong>${modeLabel}</strong>`)}
    ${hwRow("Threads", threadsLine)}
    ${hwRow("OpenCV", caps.cv_version || "unknown")}
  `;
  showModal({ title: "About", content });
}

function wireToolbar() {
  byId("tb-open").addEventListener("click", openImage);
  byId("tb-folder").addEventListener("click", openFolder);
  byId("es-open").addEventListener("click", openImage);
  byId("es-folder").addEventListener("click", openFolder);
  byId("tb-undo").addEventListener("click", undo);
  byId("tb-redo").addEventListener("click", redo);
  byId("tb-reset").addEventListener("click", resetCurrent);
  byId("tb-reset-all").addEventListener("click", resetAll);
  byId("tb-save").addEventListener("click", saveImage);
  byId("tb-save-all").addEventListener("click", saveModified);
  byId("tb-save-session").addEventListener("click", saveSession);
  byId("tb-tutorial").addEventListener("click", showTutorial);
  byId("tb-about").addEventListener("click", showAboutModal);

  byId("tb-zoom-in").addEventListener("click", () => {
    viewer.zoomBy(1.25);
    updateZoomReadout();
  });
  byId("tb-zoom-out").addEventListener("click", () => {
    viewer.zoomBy(0.8);
    updateZoomReadout();
  });
  byId("tb-fit").addEventListener("click", () => {
    viewer.fit();
    updateZoomReadout();
  });
  byId("tb-1to1").addEventListener("click", () => {
    viewer.setZoomAbsolute(1);
    updateZoomReadout();
  });

  byId("tb-sidebar").addEventListener("click", toggleCollapsed);

  byId("tb-perf").addEventListener("change", (e) => {
    const value = e.target.value;
    setState({ performanceMode: value });
    call("set_config", "performance_mode", value).catch(() => {});
  });
  byId("tb-compare").addEventListener("click", async () => {
    if (state.compareOn) {
      hideCompare();
      refreshPreview();
    } else {
      await showCompare();
    }
  });

  byId("vz-in").addEventListener("click", () => { viewer.zoomBy(1.25); updateZoomReadout(); });
  byId("vz-out").addEventListener("click", () => { viewer.zoomBy(0.8); updateZoomReadout(); });
  byId("vz-fit").addEventListener("click", () => { viewer.fit(); updateZoomReadout(); });
  byId("vz-1to1").addEventListener("click", () => { viewer.setZoomAbsolute(1); updateZoomReadout(); });
  byId("vz-compare").addEventListener("click", async () => {
    if (state.compareOn) {
      hideCompare();
      refreshPreview();
    } else {
      await showCompare();
    }
  });

  byId("nav-prev").addEventListener("click", () => navigate(-1));
  byId("nav-next").addEventListener("click", () => navigate(1));

  const wrap = document.getElementById("viewer-wrap");
  if (wrap) {
    wrap.addEventListener("mouseenter", flashNavArrows);
    wrap.addEventListener("mousemove", flashNavArrows);
    wrap.addEventListener("mouseleave", () => {
      clearTimeout(navTimer);
      const el = document.getElementById("nav-arrows");
      if (el) el.querySelectorAll("button").forEach(b => b.style.opacity = "");
    });
  }

  document.addEventListener("keydown", onKeydown);
}

function wireShortcuts() {
  const shortcuts = {
    "ctrl+o": openImage,
    "ctrl+shift+o": openFolder,
    "ctrl+s": saveImage,
    "ctrl+shift+s": saveModified,
    "ctrl+shift+a": saveSession,
    "ctrl+z": undo,
    "ctrl+y": redo,
    "ctrl+shift+z": redo,
    "ctrl+0": () => {
      viewer.fit();
      updateZoomReadout();
    },
    "1": () => switchTab("transform"),
    "2": () => switchTab("augment"),
    "3": () => switchTab("resize"),
    "4": () => switchTab("export"),
  };
  window._shortcuts = shortcuts;
}

function onKeydown(e) {
  // Never steal plain keystrokes while the user is typing in a field.
  const tag = e.target && e.target.tagName;
  const inField = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
  if (inField && !(e.ctrlKey || e.metaKey)) return;

  const mod = (e.ctrlKey || e.metaKey) ? "ctrl+" : "";
  const shift = e.shiftKey ? "shift+" : "";
  let key = e.key.toLowerCase();
  if (key === "+" || key === "=") key = "+";
  if (key === "-" || key === "_") key = "-";

  // Ctrl+Plus / Ctrl+Minus / Ctrl+0 for zoom
  if (e.ctrlKey || e.metaKey) {
    if (key === "+") {
      e.preventDefault();
      viewer.zoomBy(1.25);
      updateZoomReadout();
      return;
    }
    if (key === "-") {
      e.preventDefault();
      viewer.zoomBy(0.8);
      updateZoomReadout();
      return;
    }
  }

  const action = window._shortcuts[`${mod}${shift}${key}`] || window._shortcuts[`${mod}${key}`];
  if (action) {
    e.preventDefault();
    action();
    return;
  }

  // Prev / next image (A / D) — mirrors the original app.
  if (e.key.toLowerCase() === "a") navigate(-1);
  else if (e.key.toLowerCase() === "d") navigate(1);
}

function switchTab(id) {
  setSidebarActive(id);
}

// ---------------------------------------------------------------------------
// Backend events
// ---------------------------------------------------------------------------

function wireBackendEvents() {
  onBackend("progress", (d) => {
    if (d.message) byId("st-state").textContent = d.message;
  });
  onBackend("operation-done", () => {
    // Refresh state after batch ops complete.
    call("get_state")
      .then((p) => {
        applyBackendState(p);
        afterState();
      })
      .catch(() => {});
    updateStatusBar();
  });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function boot() {
  initProgress();
  initTitlebar();
  wireToolbar();
  wireShortcuts();
  wireBackendEvents();
  configurePanelHooks({
    viewer,
    setStatus: (t) => {
      byId("st-state").textContent = t;
    },
    afterState,
    toast: { ok, err },
  });
  initSidebar();
  initCompare();

  if (isPyWebView()) {
    try {
      const config = await call("get_config");
      setTheme(config.theme === "light" ? "light" : "dark");
      applyLayout(config.sidebar_location || "right", !!config.sidebar_collapsed);
      const perf = byId("tb-perf");
      if (perf && config.performance_mode) {
        perf.value = config.performance_mode === "low" ? "low" : "medium";
      }
      if (config.live_preview !== undefined) {
        setState({ livePreview: !!config.live_preview });
        const liveCb = document.getElementById("sb-live-preview");
        if (liveCb) liveCb.checked = !!config.live_preview;
      }
    } catch (e) {
      console.warn("config unavailable:", e);
    }
  }

  setState({ ready: true });
  updateStatusBar();
}

onReady(boot);
