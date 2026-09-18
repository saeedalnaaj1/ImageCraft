// Canvas-based image viewer: fit-to-window, cursor-anchored wheel zoom,
// drag-to-pan with edge clamping, double-click to fit.
// Crop overlay is DOM-based (positioned over the canvas) — no coordinate
// conversion during drag, just like Windows Photos.

import { setState } from "./state.js";

const MIN_SCALE = 0.05;
const MAX_SCALE = 16;
const WHEEL_STEP = 1.15;

export class Viewer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.image = null;
    this.naturalW = 0;
    this.naturalH = 0;
    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.mode = "fit";
    this.onChange = null;

    // Crop — DOM overlay. The selection rectangle is stored in *displayed
    // image pixel coordinates* (this._cropRectImg) and converted to CSS
    // pixels only for drawing, using the current view transform. Keeping the
    // source in image space means the overlay stays glued to the picture even
    // if the canvas re-renders, resizes or zooms — the old CSS-space rect
    // drifted against a moving image, which is the "jumps somewhere else" bug.
    this.cropMode = false;
    this._cropRectImg = null; // { x, y, w, h } in displayed-image pixels
    this._cropOverlay = document.getElementById("crop-overlay");
    this._cropRect = document.getElementById("crop-rect");
    this._cropDrag = null; // { kind, startX, startY, startRect (image px) }

    const host = canvas.parentElement;
    this._ro = new ResizeObserver(() => this.render());
    if (host) this._ro.observe(host);

    canvas.style.touchAction = "none";
    canvas.addEventListener("wheel", (e) => this._onWheel(e), { passive: false });
    canvas.addEventListener("pointerdown", (e) => this._onPointerDown(e));
    canvas.addEventListener("pointermove", (e) => this._onPointerMove(e));
    canvas.addEventListener("pointerup", (e) => this._onPointerUp(e));
    canvas.addEventListener("pointerleave", (e) => this._onPointerUp(e));
    canvas.addEventListener("dblclick", () => { if (!this.cropMode) this.fit(); });
    this._pointer = null;

    // Wire crop handle drag
    this._initCropHandles();
  }

  // ------------------------------------------------------------------
  // Coordinate helpers (for the image, not the crop)
  // ------------------------------------------------------------------

  _cssToImg(cssX, cssY) {
    return [(cssX - this.offsetX) / this.scale, (cssY - this.offsetY) / this.scale];
  }

  _imgToCss(ix, iy) {
    return [this.offsetX + ix * this.scale, this.offsetY + iy * this.scale];
  }

  // ------------------------------------------------------------------
  // Public API
  // ------------------------------------------------------------------

  async setImage(dataUrl, opts = {}) {
    const preserve = opts.preserveView && this.mode === "custom";
    const prevScale = this.scale;
    const prevOX = this.offsetX;
    const prevOY = this.offsetY;
    const prevNW = this.naturalW;
    const prevNH = this.naturalH;

    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        // While a crop selection is active the displayed picture is frozen so
        // the selection stays aligned with exactly what the user is looking at
        // (a debounced preview firing mid-drag used to swap the underlying
        // image, which desynced the overlay from the picture).
        if (this.cropMode) { resolve(); return; }
        this.image = img;
        this.naturalW = img.naturalWidth;
        this.naturalH = img.naturalHeight;
        if (preserve && prevNW === this.naturalW && prevNH === this.naturalH) {
          this.scale = prevScale;
          this.offsetX = prevOX;
          this.offsetY = prevOY;
          this.mode = "custom";
          this._clampOffsets();
        } else if (!this.cropMode) {
          this.fit();
        }
        this.render();
        resolve();
      };
      img.onerror = () => reject(new Error("Failed to decode image"));
      img.src = dataUrl;
    });
  }

  clear() { this.image = null; this.naturalW = 0; this.naturalH = 0; this.fit(); }
  fit() { this.mode = "fit"; this.render(); }

  zoomBy(f) {
    this._zoomTo(clamp(this.scale * f, MIN_SCALE, MAX_SCALE),
      this.canvas.clientWidth / 2, this.canvas.clientHeight / 2);
  }

  setZoomAbsolute(z) {
    this._zoomTo(clamp(z, MIN_SCALE, MAX_SCALE),
      this.canvas.clientWidth / 2, this.canvas.clientHeight / 2);
  }

  zoomPercent() { return Math.round(this.scale * 100); }

  // ------------------------------------------------------------------
  // Crop mode — DOM overlay, selection kept in image pixel space
  // ------------------------------------------------------------------

  enableCropMode() {
    if (!this.image || !this.naturalW || !this.naturalH) return false;
    this.cropMode = true;
    this.mode = "custom"; // freeze scale/offset so nothing re-fits mid-gesture
    // Start with the WHOLE picture selected — the user pulls the corners
    // inward to choose the crop region, like every photo editor.
    this._cropRectImg = { x: 0, y: 0, w: this.naturalW, h: this.naturalH };
    this._cropOverlay.hidden = false;
    this._syncCropOverlay();
    return true;
  }

  disableCropMode() {
    this.cropMode = false;
    this._cropRectImg = null;
    this._cropDrag = null;
    this._cropOverlay.hidden = true;
    this.mode = "fit";
    this.render();
  }

  resetCropRect() {
    if (!this.cropMode || !this.naturalW || !this.naturalH) return;
    this._cropRectImg = { x: 0, y: 0, w: this.naturalW, h: this.naturalH };
    this._syncCropOverlay();
  }

  /** Current selection in displayed-image pixels, or null when inactive. */
  getCropRect() {
    return this.cropMode && this._cropRectImg ? { ...this._cropRectImg } : null;
  }

  _setCropCSS(left, top, width, height) {
    const el = this._cropRect;
    el.style.left = left + "px";
    el.style.top = top + "px";
    el.style.width = width + "px";
    el.style.height = height + "px";
  }

  /** Reposition the DOM rect from the image-space selection + view transform. */
  _syncCropOverlay() {
    if (!this.cropMode || !this._cropRectImg) return;
    const { x, y, w, h } = this._cropRectImg;
    this._setCropCSS(
      Math.round(this.offsetX + x * this.scale),
      Math.round(this.offsetY + y * this.scale),
      Math.max(0, Math.round(w * this.scale)),
      Math.max(0, Math.round(h * this.scale)),
    );
  }

  /** Clamp the image-space selection to the picture, flipping past-the-edge drags. */
  _clampCropImg() {
    const r = this._cropRectImg;
    if (!r) return;
    const W = this.naturalW, H = this.naturalH;
    const minW = Math.min(8, W), minH = Math.min(8, H);
    let { x, y, w, h } = r;
    // Handle dragged across the opposite edge → flip instead of reject.
    if (w < 0) { x += w; w = -w; }
    if (h < 0) { y += h; h = -h; }
    // Slide back inside the picture.
    x = clamp(x, 0, Math.max(0, W - minW));
    y = clamp(y, 0, Math.max(0, H - minH));
    // Enforce minimum size and never exceed the remaining room.
    w = clamp(w, minW, W - x);
    h = clamp(h, minH, H - y);
    this._cropRectImg = {
      x: Math.round(x), y: Math.round(y),
      w: Math.round(w), h: Math.round(h),
    };
  }

  // ---- Handle drag wiring ----

  _initCropHandles() {
    const rect = this._cropRect;
    const overlay = this._cropOverlay;

    // Click on the darkened overlay background (outside the rect) — ignore.
    overlay.addEventListener("pointerdown", (e) => {
      if (e.target === overlay) { e.preventDefault(); return; }
    });

    // Click on crop rect body → move.
    rect.addEventListener("pointerdown", (e) => {
      if (e.target !== rect) return; // handle clicks go to handle
      if (!this.cropMode || !this._cropRectImg) return;
      e.preventDefault();
      e.stopPropagation();
      this._cropDrag = {
        kind: "move",
        startX: e.clientX,
        startY: e.clientY,
        startRect: { ...this._cropRectImg },
      };
      rect.setPointerCapture(e.pointerId);
      rect.style.cursor = "grabbing";
    });

    // Click on handle → resize.
    for (const handle of this._cropOverlay.querySelectorAll(".crop-handle")) {
      handle.addEventListener("pointerdown", (e) => {
        if (!this.cropMode || !this._cropRectImg) return;
        e.preventDefault();
        e.stopPropagation();
        this._cropDrag = {
          kind: handle.dataset.handle,
          startX: e.clientX,
          startY: e.clientY,
          startRect: { ...this._cropRectImg },
        };
        rect.setPointerCapture(e.pointerId);
      });
    }

    // Pointer move — on the rect (which has capture).
    rect.addEventListener("pointermove", (e) => {
      if (!this.cropMode || !this._cropDrag || !this._cropRectImg) return;
      e.preventDefault();
      // Convert the CSS-pixel drag delta into displayed-image pixels using the
      // frozen scale, so the selection edits in the same space it is stored.
      const s = this._cropDrag.startRect;
      const dx = (e.clientX - this._cropDrag.startX) / this.scale;
      const dy = (e.clientY - this._cropDrag.startY) / this.scale;

      let { x, y, w, h } = s;
      switch (this._cropDrag.kind) {
        case "nw": x = s.x + dx; y = s.y + dy; w = s.w - dx; h = s.h - dy; break;
        case "ne": y = s.y + dy; w = s.w + dx; h = s.h - dy; break;
        case "sw": x = s.x + dx; w = s.w - dx; h = s.h + dy; break;
        case "se": w = s.w + dx; h = s.h + dy; break;
        case "n":  y = s.y + dy; h = s.h - dy; break;
        case "s":  h = s.h + dy; break;
        case "w":  x = s.x + dx; w = s.w - dx; break;
        case "e":  w = s.w + dx; break;
        case "move": x = s.x + dx; y = s.y + dy; break;
      }
      this._cropRectImg = { x, y, w, h };
      this._clampCropImg();
      this._syncCropOverlay();
    });

    // Pointer up.
    rect.addEventListener("pointerup", () => {
      if (this._cropDrag) {
        this._cropDrag = null;
        rect.style.cursor = "move";
      }
    });
  }

  // ------------------------------------------------------------------
  // Pan / zoom interactions (on the canvas)
  // ------------------------------------------------------------------

  _onWheel(e) {
    if (!this.image) return;
    e.preventDefault();
    const rect = this.canvas.getBoundingClientRect();
    const factor = e.deltaY < 0 ? WHEEL_STEP : 1 / WHEEL_STEP;
    this._zoomTo(clamp(this.scale * factor, MIN_SCALE, MAX_SCALE),
      e.clientX - rect.left, e.clientY - rect.top);
  }

  _onPointerDown(e) {
    if (!this.image || e.button !== 0 || this.cropMode) return;
    this._pointer = { id: e.pointerId, x: e.clientX, y: e.clientY };
    this.canvas.setPointerCapture(e.pointerId);
    this.canvas.style.cursor = "grabbing";
    e.preventDefault();
  }

  _onPointerMove(e) {
    if (this.cropMode || !this._pointer || e.pointerId !== this._pointer.id) return;
    this.offsetX += e.clientX - this._pointer.x;
    this.offsetY += e.clientY - this._pointer.y;
    this._pointer = { id: e.pointerId, x: e.clientX, y: e.clientY };
    this.mode = "custom";
    this._clampOffsets();
    this.render();
  }

  _onPointerUp(e) {
    if (this._pointer && e.pointerId === this._pointer.id) {
      this._pointer = null;
      this.canvas.style.cursor = "grab";
    }
  }

  // ------------------------------------------------------------------
  // Rendering
  // ------------------------------------------------------------------

  _zoomTo(nextScale, anchorX, anchorY) {
    if (!this.image) return;
    const k = nextScale / this.scale;
    this.offsetX = anchorX - (anchorX - this.offsetX) * k;
    this.offsetY = anchorY - (anchorY - this.offsetY) * k;
    this.scale = nextScale;
    this.mode = "custom";
    this._clampOffsets();
    this.render();
  }

  _clampOffsets() {
    const cw = this.canvas.clientWidth;
    const ch = this.canvas.clientHeight;
    const iw = this.naturalW * this.scale;
    const ih = this.naturalH * this.scale;
    const cx = (cw - iw) / 2, cy = (ch - ih) / 2;
    const sx = Math.max(0, (iw - cw) / 2), sy = Math.max(0, (ih - ch) / 2);
    this.offsetX = clamp(this.offsetX, cx - sx, cx + sx);
    this.offsetY = clamp(this.offsetY, cy - sy, cy + sy);
  }

  render() {
    const canvas = this.canvas;
    const dpr = window.devicePixelRatio || 1;
    const cw = canvas.clientWidth;
    const ch = canvas.clientHeight;
    if (cw === 0 || ch === 0) return;
    if (canvas.width !== cw * dpr || canvas.height !== ch * dpr) {
      canvas.width = cw * dpr;
      canvas.height = ch * dpr;
    }

    const ctx = this.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!this.image) { canvas.style.cursor = "default"; return; }

    canvas.style.cursor = this.cropMode ? "crosshair" : (this._pointer ? "grabbing" : "grab");

    // Fit mode — recalculate ONLY when crop is off
    if (this.mode === "fit" && !this.cropMode) {
      this.scale = Math.min(1, cw / this.naturalW, ch / this.naturalH);
      this.offsetX = (cw - this.naturalW * this.scale) / 2;
      this.offsetY = (ch - this.naturalH * this.scale) / 2;
    }

    // Draw image
    ctx.setTransform(dpr * this.scale, 0, 0, dpr * this.scale, dpr * this.offsetX, dpr * this.offsetY);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(this.image, 0, 0);
    ctx.setTransform(1, 0, 0, 1, 0, 0);

    setState({ zoom: this.scale, fit: this.mode === "fit" });
    if (this.onChange) this.onChange({ scale: this.scale, percent: this.zoomPercent(), mode: this.mode });

    // Keep the crop selection glued to the picture after any re-render
    // (resize, zoom…) — the selection lives in image space, so it simply
    // follows the image wherever it is drawn.
    if (this.cropMode) this._syncCropOverlay();
  }
}

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
