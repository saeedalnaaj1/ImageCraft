// Interactive tutorial — a modal walkthrough with Previous / Next / Exit.
// Each step can open a sidebar tab and "spotlight" a real UI element so the
// user learns by seeing the actual controls.

import { setActive } from "./sidebar.js";

const STEPS = [
  {
    title: "Welcome to ImageCraft",
    body: `ImageCraft is a non-destructive image transformation and augmentation
      workbench. The original pixels are never changed on disk until you save —
      every edit can be undone. This short tour walks through the main controls.`,
  },
  {
    title: "Open your images",
    body: `Use <b>Open</b> for a single file or <b>Folder</b> to load every image in a
      directory as a batch. Shortcuts: <b>Ctrl+O</b> and <b>Ctrl+Shift+O</b>.`,
    highlight: "#tb-open",
  },
  {
    title: "Explore the viewer",
    body: `Zoom with the toolbar, the floating viewer buttons, your scroll wheel or
      <b>Ctrl +/−</b>; <b>Fit</b> and <b>1:1</b> reset the view. Use <b>Compare</b> for a
      before/after wipe, and press <b>A</b> / <b>D</b> to move between images.`,
    highlight: "#viewer-tools",
  },
  {
    title: "Transform",
    body: `The <b>Transform</b> panel adjusts geometry: rotation, scale, flips and
      perspective corner handles. Use <b>Free Crop</b> to drag a region, then
      <b>Apply</b>. Changes preview live before you commit them.`,
    tab: "transform",
    highlight: "#sidebar",
  },
  {
    title: "Augment",
    body: `The <b>Augment</b> panel mixes color, filters, geometry, flips and padding.
      Drag a slider and watch the preview. <b>Apply</b> affects the current image;
      <b>Apply to All</b> runs the same settings over the whole batch.`,
    tab: "augment",
    highlight: "#sidebar",
  },
  {
    title: "Resize",
    body: `The <b>Resize</b> panel sets an exact width/height. <b>Lock aspect ratio</b>
      keeps proportions while you type; <b>Apply to All</b> resizes the batch.`,
    tab: "resize",
    highlight: "#sidebar",
  },
  {
    title: "Save and export",
    body: `<b>Save</b> writes the current image. <b>Save Modified</b> saves only images
      you changed, while <b>Save All</b> saves every image in the session — edited
      or not. Add a filename prefix/postfix in the <b>Export</b> panel.`,
    tab: "export",
    highlight: "#tb-save-session",
  },
  {
    title: "Undo, redo, reset",
    body: `<b>Undo</b> / <b>Redo</b> (<b>Ctrl+Z</b> / <b>Ctrl+Y</b>) step through your edit
      history, including batch edits. <b>Reset</b> reverts the current image and
      <b>Reset All</b> reverts the whole batch to the originals.`,
    highlight: "#tb-undo",
  },
  {
    title: "Performance profiles",
    body: `Pick <b>Perf: High</b> to use the GPU (OpenCL) and all CPU cores, or
      <b>Perf: Low</b> for CPU-only single-threaded work on machines without a
      dedicated GPU. <b>About</b> shows exactly what hardware was detected.`,
    highlight: "#tb-perf",
  },
  {
    title: "You're ready",
    body: `That's the tour. Open an image or a folder and start experimenting — the
      live preview and universal undo make it safe to try things. You can replay
      this tutorial any time from the <b>Tutorial</b> button.`,
  },
];

export function showTutorial() {
  let index = 0;
  let spotlit = null;

  const clearSpotlight = () => {
    if (spotlit) {
      spotlit.classList.remove("tutorial-spotlight");
      spotlit = null;
    }
  };

  const applySpotlight = (selector) => {
    clearSpotlight();
    if (!selector) return;
    const el = document.querySelector(selector);
    if (!el) return;
    spotlit = el;
    el.classList.add("tutorial-spotlight");
    try {
      el.scrollIntoView({ block: "nearest", inline: "nearest" });
    } catch (_) { /* older engines */ }
  };

  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop tutorial-backdrop";

  const modal = document.createElement("div");
  modal.className = "modal tutorial-modal";

  const header = document.createElement("div");
  header.className = "modal-header";
  const titleEl = document.createElement("h2");
  titleEl.className = "modal-title";
  titleEl.textContent = "Tutorial";
  const closeBtn = document.createElement("button");
  closeBtn.className = "modal-close";
  closeBtn.textContent = "✕";
  closeBtn.title = "Exit tutorial";
  closeBtn.addEventListener("click", close);
  header.append(titleEl, closeBtn);

  const body = document.createElement("div");
  body.className = "modal-body";
  const stepTitle = document.createElement("h3");
  stepTitle.className = "tutorial-step-title";
  const stepText = document.createElement("div");
  stepText.className = "tutorial-step-text";
  body.append(stepTitle, stepText);

  const footer = document.createElement("div");
  footer.className = "tutorial-footer";
  const counter = document.createElement("span");
  counter.className = "tutorial-counter";
  const prevBtn = mkButton("‹ Previous", () => go(-1));
  const nextBtn = mkButton("Next ›", () => go(1));
  const exitBtn = mkButton("Exit", close);
  exitBtn.className = "tutorial-exit";
  const nav = document.createElement("div");
  nav.className = "tutorial-nav";
  nav.append(prevBtn, nextBtn, exitBtn);
  footer.append(counter, nav);

  modal.append(header, body, footer);
  backdrop.append(modal);
  document.body.append(backdrop);

  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) close();
  });
  document.addEventListener("keydown", onKey);

  function mkButton(label, fn) {
    const b = document.createElement("button");
    b.textContent = label;
    b.addEventListener("click", fn);
    return b;
  }

  function onKey(e) {
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "ArrowRight") { e.preventDefault(); go(1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); }
  }

  function render() {
    const step = STEPS[index];
    if (step.tab) setActive(step.tab);
    stepTitle.textContent = step.title;
    stepText.innerHTML = step.body;
    counter.textContent = `Step ${index + 1} of ${STEPS.length}`;
    prevBtn.disabled = index === 0;
    nextBtn.textContent = index === STEPS.length - 1 ? "Finish" : "Next ›";
    applySpotlight(step.highlight);
  }

  function go(delta) {
    if (delta > 0 && index === STEPS.length - 1) { close(); return; }
    index = Math.min(STEPS.length - 1, Math.max(0, index + delta));
    render();
  }

  function close() {
    clearSpotlight();
    document.removeEventListener("keydown", onKey);
    backdrop.remove();
  }

  render();
  return { close };
}
